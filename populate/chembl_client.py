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

from config import CHEMBL_BASE, MAX_BIOACT
from http_retry import get_with_retry

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


# ============================================================
# Compostos
# ============================================================

def fetch_compound(chembl_id: str) -> Optional[dict]:
    """
    Busca dados estruturais e propriedades ADMET de um composto.
    O dict retornado inclui uma chave 'admet' com todas as propriedades
    moleculares calculadas — sem requisição extra.
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
            "inchi_key":          structs.get("standard_inchi_key"),
            "alogp":              props.get("alogp"),
            "hbd":                props.get("hbd"),
            "hba":                props.get("hba"),
            "psa":                props.get("psa"),
            "ro5_violations":     props.get("num_ro5_violations"),
        }

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


# ============================================================
# Alvos
# ============================================================

def fetch_target(target_chembl_id: str) -> Optional[dict]:
    """Busca nome, tipo e organismo de um alvo biológico."""
    try:
        r = get_with_retry(
            f"{CHEMBL_BASE}/target/{target_chembl_id}.json", timeout=20
        )
        data = r.json()
        return {
            "chembl_id": target_chembl_id,
            "name":      data.get("pref_name") or target_chembl_id,
            "type":      data.get("target_type"),
            "organism":  data.get("organism"),
        }
    except Exception as exc:
        log.error(f"Erro ao buscar alvo {target_chembl_id}: {exc}")
        return None


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