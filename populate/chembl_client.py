"""
chembl_client.py
----------------
Funções de busca na API do ChEMBL.

Endpoints usados:
  /molecule/{id}          — dados estruturais e ADMET
  /activity               — bioatividades
  /target/{id}            — alvos biológicos
  /drug_indication        — indicações terapêuticas
  /mechanism              — mecanismos de ação
"""

import logging
import time
from typing import Optional

import requests

from .config import CHEMBL_BASE, MAX_BIOACT
from .http_retry import get_with_retry

log = logging.getLogger(__name__)


# ============================================================
# Utilitários
# ============================================================

def to_numeric(value) -> Optional[float]:
    """Converte string ou número para float. Retorna None se falhar."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _to_bool(value) -> Optional[bool]:
    """ChEMBL usa true/false, 1/0 e null — normaliza para bool ou None."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("true", "t", "1", "yes", "y"):
            return True
        if v in ("false", "f", "0", "no", "n", ""):
            return False
    return None


def _extract_synonyms(raw) -> list:
    """
    Normaliza `molecule_synonyms` do ChEMBL para [{synonym, syn_type}, ...].
    Deduplica por (synonym, syn_type) — o ChEMBL repete entradas (BAN/INN/etc).
    """
    if not raw:
        return []
    seen = set()
    out  = []
    for s in raw:
        if not isinstance(s, dict):
            continue
        name = s.get("molecule_synonym") or s.get("synonyms")
        if not name:
            continue
        syn_type = s.get("syn_type")
        key = (name.strip(), syn_type)
        if key in seen:
            continue
        seen.add(key)
        out.append({"synonym": name.strip(), "syn_type": syn_type})
    return out


def _extract_atc(raw) -> list:
    """
    Normaliza `atc_classifications` para lista de dicts com level1..5 + descrições.
    Ignora entradas sem level5 (código completo ATC).
    """
    if not raw:
        return []
    out = []
    for atc in raw:
        if not isinstance(atc, dict):
            continue
        level5 = atc.get("level5")
        if not level5:
            continue
        out.append({
            "level5":             level5,
            "level1":             atc.get("level1"),
            "level1_description": atc.get("level1_description"),
            "level2":             atc.get("level2"),
            "level2_description": atc.get("level2_description"),
            "level3":             atc.get("level3"),
            "level3_description": atc.get("level3_description"),
            "level4":             atc.get("level4"),
            "level4_description": atc.get("level4_description"),
        })
    return out


# ============================================================
# Compostos
# ============================================================

def fetch_compound(chembl_id: str) -> Optional[dict]:
    """
    Busca dados estruturais, propriedades ADMET e metadata clínico/regulatório
    de um composto. O dict retornado inclui as chaves:
      - 'admet'     propriedades moleculares calculadas
      - 'synonyms'  lista de {synonym, syn_type} (INN, BAN, trade names, ...)
      - 'atc'      lista de {level5, level1..4, *_description}

    Tudo extraído da mesma requisição /molecule/{id} — sem chamada extra.
    """
    try:
        r = get_with_retry(f"{CHEMBL_BASE}/molecule/{chembl_id}.json", timeout=20)
        data    = r.json()
        props   = data.get("molecule_properties") or {}
        structs = data.get("molecule_structures") or {}

        compound = {
            "chembl_id":          chembl_id,
            "name":               data.get("pref_name") or chembl_id,
            "molecular_formula":  props.get("full_molformula"),
            "mol_weight":         props.get("full_mwt"),
            "smiles":             structs.get("canonical_smiles"),
            "inchi":              structs.get("standard_inchi"),
            "inchi_key":          structs.get("standard_inchi_key"),
            "alogp":              props.get("alogp"),
            "hbd":                props.get("hbd"),
            "hba":                props.get("hba"),
            "psa":                props.get("psa"),
            "ro5_violations":     props.get("num_ro5_violations"),

            # ── Fase clínica / aprovação ───────────────────────
            "max_phase":          to_numeric(data.get("max_phase")),
            "first_approval":     data.get("first_approval"),
            "molecule_type":      data.get("molecule_type"),

            # ── Vias de administração ──────────────────────────
            # ChEMBL usa 0/1 — _to_bool aceita ambos os formatos.
            "oral":               _to_bool(data.get("oral")),
            "parenteral":         _to_bool(data.get("parenteral")),
            "topical":            _to_bool(data.get("topical")),

            # ── Segurança / status regulatório ─────────────────
            "black_box_warning":  _to_bool(data.get("black_box_warning")),
            "withdrawn_flag":     _to_bool(data.get("withdrawn_flag")),
            "withdrawn_reason":   data.get("withdrawn_reason"),
            "withdrawn_year":     data.get("withdrawn_year"),
            "withdrawn_country":  data.get("withdrawn_country"),
            "withdrawn_class":    data.get("withdrawn_class"),

            # ── Flags qualitativos ─────────────────────────────
            "prodrug":            _to_bool(data.get("prodrug")),
            "natural_product":    _to_bool(data.get("natural_product")),
            "therapeutic_flag":   _to_bool(data.get("therapeutic_flag")),
            "first_in_class":     _to_bool(data.get("first_in_class")),
            "orphan":             _to_bool(data.get("orphan")),
            "chirality":          data.get("chirality"),
            "availability_type":  data.get("availability_type"),

            # ── USAN stem (classifica drogas pelo sufixo: -tinib, -mab…) ──
            "usan_stem":            data.get("usan_stem"),
            "usan_stem_definition": data.get("usan_stem_definition"),
            "usan_year":            data.get("usan_year"),

            # ── Outros ─────────────────────────────────────────
            "np_likeness_score":  to_numeric(props.get("np_likeness_score")),
        }

        compound["synonyms"] = _extract_synonyms(data.get("molecule_synonyms"))
        compound["atc"]      = _extract_atc(data.get("atc_classifications"))

        compound["admet"] = {
            "alogp":              props.get("alogp"),
            "cx_logp":            props.get("cx_logp"),
            "cx_logd":            props.get("cx_logd"),
            "cx_most_apka":       props.get("cx_most_apka"),
            "cx_most_bpka":       props.get("cx_most_bpka"),
            "molecular_species":  props.get("molecular_species"),
            "mw_freebase":        props.get("mw_freebase"),
            "mw_monoisotopic":    props.get("mw_monoisotopic"),
            "heavy_atoms":        props.get("heavy_atoms"),
            "aromatic_rings":     props.get("aromatic_rings"),
            "rtb":                props.get("rtb"),
            "hbd":                props.get("hbd"),
            "hbd_lipinski":       props.get("hbd_lipinski"),
            "hba":                props.get("hba"),
            "hba_lipinski":       props.get("hba_lipinski"),
            "psa":                props.get("psa"),
            "num_ro5_violations": props.get("num_ro5_violations"),
            "ro3_pass":           props.get("ro3_pass"),
            "qed_weighted":       props.get("qed_weighted"),
            "num_alerts":         props.get("num_alerts"),
        }

        return compound
    except Exception as exc:
        log.error(f"Erro ao buscar composto {chembl_id}: {exc}")
        return None


def fetch_bioactivities(chembl_id: str) -> list:
    """Busca as primeiras MAX_BIOACT bioatividades de um composto."""
    try:
        r = get_with_retry(
            f"{CHEMBL_BASE}/activity.json",
            params={"molecule_chembl_id": chembl_id, "limit": MAX_BIOACT},
            timeout=20,
        )
        return r.json().get("activities", [])
    except Exception as exc:
        log.error(f"Erro ao buscar bioatividades de {chembl_id}: {exc}")
        return []


def normalize_bioactivity(act: dict) -> dict:
    """
    Normaliza um dict cru da API /activity para a forma esperada por
    upsert_bioactivity. Extrai pchembl, dados do ensaio, organismo, jornal,
    ligand efficiency e variantes.

    Retorna chaves None para campos ausentes — psycopg2 grava NULL.
    """
    le = act.get("ligand_efficiency") or {}

    # target_tax_id chega como string ("9606") — converter, mas tolerar não-numéricos
    tax_id = act.get("target_tax_id")
    try:
        tax_id = int(tax_id) if tax_id not in (None, "") else None
    except (ValueError, TypeError):
        tax_id = None

    doc_year = act.get("document_year")
    try:
        doc_year = int(doc_year) if doc_year not in (None, "") else None
    except (ValueError, TypeError):
        doc_year = None

    activity_id = act.get("activity_id")
    try:
        activity_id = int(activity_id) if activity_id is not None else None
    except (ValueError, TypeError):
        activity_id = None

    return {
        "activity_id":     activity_id,

        # Valores reportados (mantidos para compat com a tabela original)
        "type":            act.get("type")     or act.get("standard_type"),
        "value":           to_numeric(act.get("value")),
        "units":           act.get("units")    or act.get("standard_units"),
        "relation":        act.get("relation") or act.get("standard_relation"),

        # Valores padronizados pelo ChEMBL
        "standard_value":  to_numeric(act.get("standard_value")),
        "standard_units":  act.get("standard_units"),

        # pChEMBL — métrica padrão de potência
        "pchembl_value":   to_numeric(act.get("pchembl_value")),

        # Ensaio
        "assay_chembl_id":   act.get("assay_chembl_id"),
        "assay_description": act.get("assay_description"),
        "assay_type":        act.get("assay_type"),
        "bao_label":         act.get("bao_label"),

        # Alvo
        "target_chembl_id": act.get("target_chembl_id"),
        "target_pref_name": act.get("target_pref_name"),
        "target_organism":  act.get("target_organism"),
        "target_tax_id":    tax_id,

        # Documento (referência bibliográfica da medida)
        "document_chembl_id": act.get("document_chembl_id"),
        "document_journal":   act.get("document_journal"),
        "document_year":      doc_year,

        # Ligand Efficiency Metrics
        "bei": to_numeric(le.get("bei")),
        "le":  to_numeric(le.get("le")),
        "lle": to_numeric(le.get("lle")),
        "sei": to_numeric(le.get("sei")),

        # Flags de qualidade
        "data_validity_comment": act.get("data_validity_comment"),
        "activity_comment":      act.get("activity_comment"),
        "potential_duplicate":   _to_bool(act.get("potential_duplicate")),

        # Variantes (mutações estudadas no ensaio)
        "assay_variant_accession": act.get("assay_variant_accession"),
        "assay_variant_mutation":  act.get("assay_variant_mutation"),
    }


# ============================================================
# Alvos
# ============================================================

def fetch_target(target_chembl_id: str) -> Optional[dict]:
    """
    Busca dados de um alvo biológico (proteína, complexo, etc.).

    Retorna um dict com:
      - campos base (chembl_id, name, type, organism)
      - tax_id, species_group_flag (migration 0006)
      - components: lista de subunidades com UniProt/gene_symbol/type
        e xrefs (PDB, GO, Reactome, InterPro, …)

    Tudo extraído da mesma requisição /target/{id} — sem chamada extra.
    """
    try:
        r = get_with_retry(
            f"{CHEMBL_BASE}/target/{target_chembl_id}.json", timeout=20
        )
        data = r.json()

        tax_id = data.get("tax_id")
        try:
            tax_id = int(tax_id) if tax_id not in (None, "") else None
        except (ValueError, TypeError):
            tax_id = None

        return {
            "chembl_id":           target_chembl_id,
            "name":                data.get("pref_name") or target_chembl_id,
            "type":                data.get("target_type"),
            "organism":            data.get("organism"),
            "tax_id":              tax_id,
            "species_group_flag":  _to_bool(data.get("species_group_flag")),
            "components":          _extract_target_components(data.get("target_components")),
        }
    except Exception as exc:
        log.error(f"Erro ao buscar alvo {target_chembl_id}: {exc}")
        return None


def _extract_target_components(raw) -> list:
    """
    Normaliza `target_components` do ChEMBL.

    Cada componente vira:
      {component_id, accession, gene_symbol, component_type,
       component_description, relationship, xrefs: [...]}

    `gene_symbol` é inferido de target_component_synonyms quando o ChEMBL
    não traz no nível raiz (caminho comum: GENE_SYMBOL syn_type).
    """
    if not raw:
        return []
    out = []
    for comp in raw:
        if not isinstance(comp, dict):
            continue

        # gene_symbol às vezes só está nos synonyms do componente.
        gene_symbol = comp.get("gene_symbol")
        if not gene_symbol:
            for syn in comp.get("target_component_synonyms") or []:
                if isinstance(syn, dict) and syn.get("syn_type") == "GENE_SYMBOL":
                    gene_symbol = syn.get("component_synonym")
                    break

        out.append({
            "component_id":          comp.get("component_id"),
            "accession":             comp.get("accession"),
            "gene_symbol":           gene_symbol,
            "component_type":        comp.get("component_type"),
            "component_description": comp.get("component_description"),
            "relationship":          comp.get("relationship"),
            "xrefs":                 _extract_target_xrefs(comp.get("target_component_xrefs")),
        })
    return out


def _extract_target_xrefs(raw) -> list:
    """
    Normaliza target_component_xrefs para [{src_db, xref_id, xref_name}, ...].
    Deduplica entradas idênticas e ignora as sem src_db/xref_id.
    """
    if not raw:
        return []
    seen = set()
    out  = []
    for x in raw:
        if not isinstance(x, dict):
            continue
        src_db  = x.get("xref_src_db")
        xref_id = x.get("xref_id")
        if not src_db or not xref_id:
            continue
        key = (src_db, xref_id)
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "xref_src_db": src_db,
            "xref_id":     xref_id,
            "xref_name":   x.get("xref_name"),
        })
    return out


# ============================================================
# Indicações terapêuticas
# ============================================================

def fetch_indications(chembl_id: str) -> list:
    """
    Busca todas as indicações terapêuticas via /drug_indication.
    Faz paginação automática para retornar a lista completa.

    Cada entrada contém:
      drugind_id       — PK único no ChEMBL
      mesh_id/heading  — doença pelo vocabulário MeSH
      efo_id/term      — doença pelo vocabulário EFO
      max_phase_for_ind— fase clínica máxima (4 = aprovado)
    """
    indications = []
    offset, limit = 0, 100

    while True:
        try:
            r = get_with_retry(
                f"{CHEMBL_BASE}/drug_indication.json",
                params={
                    "molecule_chembl_id": chembl_id,
                    "limit":             limit,
                    "offset":            offset,
                },
                timeout=20,
            )
            data  = r.json()
            batch = data.get("drug_indications", [])
            indications.extend(batch)

            total   = data.get("page_meta", {}).get("total_count", 0)
            offset += limit
            if offset >= total:
                break

            time.sleep(0.2)

        except Exception as exc:
            log.error(f"Erro ao buscar indicacoes de {chembl_id}: {exc}")
            break

    return indications


# ============================================================
# Mecanismos de ação
# ============================================================

def fetch_mechanisms(chembl_id: str) -> list:
    """
    Busca mecanismos de ação via /mechanism.

    Campos relevantes:
      mec_id               — PK único no ChEMBL
      mechanism_of_action  — ex: "Cyclooxygenase inhibitor"
      action_type          — INHIBITOR | AGONIST | ANTAGONIST | BLOCKER | ...
      target_chembl_id     — alvo associado
      target_name          — nome do alvo (desnormalizado)
      direct_interaction   — True se interage diretamente com o alvo
      disease_efficacy     — True se relevante para a eficácia terapêutica
    """
    try:
        r = get_with_retry(
            f"{CHEMBL_BASE}/mechanism.json",
            params={"molecule_chembl_id": chembl_id, "limit": 100},
            timeout=20,
        )
        return r.json().get("mechanisms", [])
    except Exception as exc:
        log.error(f"Erro ao buscar mecanismos de {chembl_id}: {exc}")
        return []