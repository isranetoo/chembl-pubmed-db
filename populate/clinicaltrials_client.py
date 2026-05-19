"""
clinicaltrials_client.py — Cliente ClinicalTrials.gov v2 para o DrugXpert
========================================================================

Busca ensaios clínicos por intervenção (nome do fármaco) na API pública
da ClinicalTrials.gov v2, normaliza o JSON aninhado num shape plano e
faz upsert no cache local (clinical_trials + compound_clinical_trials).

Convenções:
- Sync, com httpx.Client. Combina com o resto do projeto (api.py é todo
  sync, pool psycopg2 é sync).
- sync_compound_trials recebe um cursor e NÃO commita — quem chama é
  dono da transação (a rota faz commit/rollback).

API: https://clinicaltrials.gov/api/v2/studies
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import date
from typing import Iterable, Iterator

import requests
from psycopg2.extras import execute_values

log = logging.getLogger("clinicaltrials_client")

CT_GOV_BASE = "https://clinicaltrials.gov/api/v2/studies"

# Usamos `requests` (não httpx) porque o WAF da CT.gov (Istio Envoy) bloqueia
# o fingerprint TLS/HTTP do httpx com 403, mesmo com UA de browser. O stack
# do `requests` (urllib3) passa consistentemente — testado lado-a-lado contra
# o mesmo endpoint, mesma UA, mesmo IP. Também alinha com o resto do projeto:
# chembl_client / pubmed_client / owkin_client já usam requests.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept":          "*/*",
    "Accept-Language": "en-US,en;q=0.9",
}

# Retry pra 403/429/5xx: bloqueio do WAF e rate-limit costumam ser
# transientes (~10-30s). Backoff dobra a cada tentativa.
RETRY_STATUS  = {403, 429, 500, 502, 503, 504}
RETRY_MAX     = 3
RETRY_BACKOFF = 5.0   # segundos da primeira espera; dobra a cada tentativa

# Limite de páginas pra evitar runaway num drug muito popular. 10 * 100
# = 1000 trials cobre folgado até o imatinib (~700).
MAX_PAGES = 10
PAGE_SIZE = 100

# Sufixos de sal/forma removidos pra match "normalized". Do mais longo
# pro mais curto pra não comer "sodium" antes de algo mais específico.
SALT_SUFFIXES = (
    "hydrochloride", "mesylate", "phosphate", "succinate", "fumarate",
    "tartrate", "sulfate", "maleate", "acetate", "citrate",
    "sodium", "potassium", "calcium",
)

# Enums espelhados do SQL — usados pra normalizar valores desconhecidos
# em vez de quebrar o INSERT com violation de enum.
_VALID_STATUS = {
    "NOT_YET_RECRUITING", "RECRUITING", "ENROLLING_BY_INVITATION",
    "ACTIVE_NOT_RECRUITING", "SUSPENDED", "TERMINATED", "COMPLETED",
    "WITHDRAWN", "UNKNOWN", "APPROVED_FOR_MARKETING",
    "AVAILABLE", "NO_LONGER_AVAILABLE", "TEMPORARILY_NOT_AVAILABLE",
    "WITHHELD",
}
_VALID_PHASES = {"EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4", "NA"}
_VALID_STUDY_TYPES = {"INTERVENTIONAL", "OBSERVATIONAL", "EXPANDED_ACCESS"}


# ============================================================
# Fetch
# ============================================================

def _get_with_retry(session: requests.Session, params: dict) -> requests.Response:
    """GET com backoff exponencial em 403/429/5xx."""
    wait = RETRY_BACKOFF
    last_exc: Exception | None = None
    for attempt in range(1, RETRY_MAX + 1):
        try:
            r = session.get(CT_GOV_BASE, params=params, timeout=30)
        except requests.RequestException as exc:
            last_exc = exc
            if attempt == RETRY_MAX:
                raise
            log.warning("ct.gov network error (try %d/%d): %s — sleeping %.0fs",
                        attempt, RETRY_MAX, exc, wait)
            time.sleep(wait)
            wait *= 2
            continue

        if r.status_code not in RETRY_STATUS:
            r.raise_for_status()
            return r

        if attempt == RETRY_MAX:
            r.raise_for_status()  # propaga o erro final
        log.warning("ct.gov %d (try %d/%d) — sleeping %.0fs",
                    r.status_code, attempt, RETRY_MAX, wait)
        time.sleep(wait)
        wait *= 2

    if last_exc:
        raise last_exc
    raise RuntimeError("retry loop exhausted without response")


def fetch_trials_by_intervention(drug_name: str) -> list[dict]:
    """
    Pagina /studies?query.intr={drug} via nextPageToken até esgotar
    ou bater MAX_PAGES. Retorna a lista bruta de `studies` agregada.
    """
    all_studies: list[dict] = []
    next_token: str | None = None

    with requests.Session() as session:
        session.headers.update(HEADERS)
        for page in range(1, MAX_PAGES + 1):
            params = {
                "query.intr": drug_name,
                "pageSize":   PAGE_SIZE,
                "format":     "json",
            }
            if next_token:
                params["pageToken"] = next_token

            r = _get_with_retry(session, params)
            payload = r.json()

            studies = payload.get("studies") or []
            all_studies.extend(studies)
            log.info(
                "ct.gov page %d for '%s': %d trials (total=%d)",
                page, drug_name, len(studies), len(all_studies),
            )

            next_token = payload.get("nextPageToken")
            if not next_token or not studies:
                break

    return all_studies


# ============================================================
# Normalização
# ============================================================

def _parse_partial_date(raw: str | None) -> date | None:
    """Aceita YYYY-MM-DD e YYYY-MM (preenche dia=01). Retorna None caso contrário."""
    if not raw or not isinstance(raw, str):
        return None
    try:
        if len(raw) == 7:
            return date.fromisoformat(f"{raw}-01")
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _coerce_status(value: str | None) -> str:
    return value if value in _VALID_STATUS else "UNKNOWN"


def _coerce_phases(values: Iterable[str] | None) -> list[str]:
    if not values:
        return []
    return [v for v in values if v in _VALID_PHASES]


def _coerce_study_type(value: str | None) -> str | None:
    return value if value in _VALID_STUDY_TYPES else None


def _normalize_trial(study: dict) -> dict:
    """Achata o protocolSection num dict plano; guarda o study inteiro em raw."""
    ps = study.get("protocolSection") or {}

    ident    = ps.get("identificationModule")        or {}
    status_  = ps.get("statusModule")                or {}
    design   = ps.get("designModule")                or {}
    cond     = ps.get("conditionsModule")            or {}
    arms     = ps.get("armsInterventionsModule")     or {}
    sponsor  = ps.get("sponsorCollaboratorsModule")  or {}
    locs     = ps.get("contactsLocationsModule")     or {}
    outcomes = ps.get("outcomesModule")              or {}

    interventions = [
        i.get("name") for i in (arms.get("interventions") or []) if i.get("name")
    ]
    conditions = list(cond.get("conditions") or [])

    primary_outcomes = outcomes.get("primaryOutcomes") or []
    primary_endpoint = (primary_outcomes[0].get("measure")
                        if primary_outcomes else None)

    enrollment_info = design.get("enrollmentInfo") or {}
    raw_enrollment = enrollment_info.get("count")
    try:
        enrollment = int(raw_enrollment) if raw_enrollment is not None else None
    except (TypeError, ValueError):
        enrollment = None

    return {
        "nct_id":                  ident.get("nctId"),
        "title":                   ident.get("briefTitle") or ident.get("officialTitle"),
        "status":                  _coerce_status(status_.get("overallStatus")),
        "phases":                  _coerce_phases(design.get("phases")),
        "conditions":              conditions,
        "interventions":           interventions,
        "sponsor":                 (sponsor.get("leadSponsor") or {}).get("name"),
        "enrollment":              enrollment,
        "start_date":              _parse_partial_date(
                                        (status_.get("startDateStruct") or {}).get("date")
                                    ),
        "primary_completion_date": _parse_partial_date(
                                        (status_.get("primaryCompletionDateStruct") or {}).get("date")
                                    ),
        "locations_count":         len(locs.get("locations") or []),
        "study_type":              _coerce_study_type(design.get("studyType")),
        "primary_endpoint":        primary_endpoint,
        "raw":                     study,
    }


# ============================================================
# Match classification
# ============================================================

_SALT_RX = re.compile(
    r"\s+(?:" + "|".join(re.escape(s) for s in SALT_SUFFIXES) + r")\b",
    flags=re.IGNORECASE,
)


def _strip_salts(name: str) -> str:
    """Itera até estável — pega "X sodium dihydrate" → "X" em múltiplas passadas."""
    prev, curr = None, name.strip()
    while prev != curr:
        prev = curr
        curr = _SALT_RX.sub("", curr).strip()
    return curr


def _classify_match(intervention_name: str, target_drug_name: str) -> tuple[str, float]:
    """
    Retorna (match_method, confidence):
      exact_name (1.00) > normalized (0.95) > fuzzy substring (0.80) > fuzzy (0.50)
    """
    a = (intervention_name or "").strip().lower()
    b = (target_drug_name or "").strip().lower()
    if not a or not b:
        return ("fuzzy", 0.50)

    if a == b:
        return ("exact_name", 1.00)

    if _strip_salts(a) == _strip_salts(b):
        return ("normalized", 0.95)

    if b in a or a in b:
        return ("fuzzy", 0.80)

    return ("fuzzy", 0.50)


def _best_match_for_trial(
    interventions: list[str], drug_name: str
) -> tuple[str, str, float] | None:
    """(intervention, method, confidence) com maior conf. None se vazio."""
    if not interventions:
        return None
    best: tuple[str, str, float] | None = None
    for intr in interventions:
        method, conf = _classify_match(intr, drug_name)
        if best is None or conf > best[2]:
            best = (intr, method, conf)
    return best


# ============================================================
# Pipeline: sync
# ============================================================

def _chunks(seq: list, size: int) -> Iterator[list]:
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


_UPSERT_TRIAL_SQL = """
    INSERT INTO clinical_trials (
        nct_id, title, status, phases, conditions, interventions,
        sponsor, enrollment, start_date, primary_completion_date,
        locations_count, study_type, primary_endpoint, raw, last_synced_at
    ) VALUES %s
    ON CONFLICT (nct_id) DO UPDATE SET
        title                   = EXCLUDED.title,
        status                  = EXCLUDED.status,
        phases                  = EXCLUDED.phases,
        conditions              = EXCLUDED.conditions,
        interventions           = EXCLUDED.interventions,
        sponsor                 = EXCLUDED.sponsor,
        enrollment              = EXCLUDED.enrollment,
        start_date              = EXCLUDED.start_date,
        primary_completion_date = EXCLUDED.primary_completion_date,
        locations_count         = EXCLUDED.locations_count,
        study_type              = EXCLUDED.study_type,
        primary_endpoint        = EXCLUDED.primary_endpoint,
        raw                     = EXCLUDED.raw,
        last_synced_at          = EXCLUDED.last_synced_at
"""

# Casts pra enums e jsonb (psycopg2 não infere quando vem de execute_values).
_UPSERT_TRIAL_TEMPLATE = (
    "(%s, %s, %s::trial_status, %s::trial_phase[], %s::text[], %s::text[], "
    "%s, %s, %s, %s, %s, %s::trial_study_type, %s, %s::jsonb, NOW())"
)

_UPSERT_LINK_SQL = """
    INSERT INTO compound_clinical_trials (
        chembl_id, nct_id, intervention_name, match_method, match_confidence
    ) VALUES %s
    ON CONFLICT (chembl_id, nct_id) DO UPDATE SET
        intervention_name = EXCLUDED.intervention_name,
        match_method      = EXCLUDED.match_method,
        match_confidence  = EXCLUDED.match_confidence
"""
_UPSERT_LINK_TEMPLATE = "(%s, %s, %s, %s::intervention_match_method, %s)"

BATCH = 500
MIN_CONFIDENCE = 0.50


def sync_compound_trials(cur, chembl_id: str, drug_name: str) -> dict[str, int]:
    """
    Pipeline ponta-a-ponta:
        1. Busca trials da CT.gov pelo nome
        2. Normaliza
        3. Upsert em clinical_trials (batch 500)
        4. Cria links em compound_clinical_trials (1 melhor intervenção
           por trial, descartando match_confidence < 0.50)
    Caller é responsável por commit/rollback.
    """
    chembl_id = chembl_id.upper().strip()
    studies = fetch_trials_by_intervention(drug_name)
    log.info("ct.gov returned %d studies for '%s'", len(studies), drug_name)

    normalized: list[dict] = [
        n for n in (_normalize_trial(s) for s in studies) if n["nct_id"]
    ]

    trial_rows = [
        (
            n["nct_id"], n["title"], n["status"], n["phases"],
            n["conditions"], n["interventions"], n["sponsor"],
            n["enrollment"], n["start_date"], n["primary_completion_date"],
            n["locations_count"], n["study_type"], n["primary_endpoint"],
            json.dumps(n["raw"]),
        )
        for n in normalized
    ]
    upserted = 0
    for chunk in _chunks(trial_rows, BATCH):
        execute_values(cur, _UPSERT_TRIAL_SQL, chunk,
                       template=_UPSERT_TRIAL_TEMPLATE)
        upserted += len(chunk)

    link_rows: list[tuple] = []
    for n in normalized:
        best = _best_match_for_trial(n["interventions"], drug_name)
        if best is None:
            continue
        intr, method, conf = best
        if conf < MIN_CONFIDENCE:
            continue
        link_rows.append((chembl_id, n["nct_id"], intr, method, conf))

    links = 0
    for chunk in _chunks(link_rows, BATCH):
        execute_values(cur, _UPSERT_LINK_SQL, chunk,
                       template=_UPSERT_LINK_TEMPLATE)
        links += len(chunk)

    log.info(
        "sync %s/%s: fetched=%d upserted=%d links=%d",
        chembl_id, drug_name, len(studies), upserted, links,
    )

    return {
        "trials_fetched":  len(studies),
        "trials_upserted": upserted,
        "links_created":   links,
    }
