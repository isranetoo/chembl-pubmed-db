"""
populate.py
-----------
Ponto de entrada principal. Orquestra a coleta e persistência dos dados.

Uso:
    python populate.py

Módulos:
    config          — constantes, DB_CONFIG, lista de compostos
    chembl_client   — busca de compostos, alvos, indicações e mecanismos
    pubmed_client   — busca de artigos e parsing de XML
    db              — inserções e upserts no PostgreSQL
"""

import json
import logging
import time

import psycopg2

from config import DB_CONFIG, POPULAR_COMPOUNDS
from chembl_client import (
    fetch_compound,
    fetch_bioactivities,
    fetch_target,
    fetch_indications,
    fetch_mechanisms,
    to_numeric,
)
from pubmed_client import search_pubmed, fetch_articles
from db import (
    get_compound_status,
    upsert_compound,
    upsert_target,
    insert_bioactivity,
    upsert_indication,
    upsert_mechanism,
    upsert_admet,
    upsert_article,
    link_article_compound,
)

log = logging.getLogger(__name__)


def main():
    log.info("Conectando ao banco de dados...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur  = conn.cursor()

    # Contadores para o resumo final
    stats = {"novos": 0, "completos": 0, "parciais": 0, "erros": 0}

    for chembl_id, common_name in POPULAR_COMPOUNDS:
        log.info("=" * 55)
        log.info(f"Processando: {common_name} ({chembl_id})")

        # ── Checar o que já existe no banco ───────────────────
        status = get_compound_status(cur, chembl_id)

        if status and status["is_complete"]:
            log.info("  Ja completo — pulando.")
            stats["completos"] += 1
            continue

        # Identificar etapas faltando (para log informativo)
        if status:
            faltando = [
                etapa for etapa, chave in [
                    ("admet",        "has_admet"),
                    ("bioatividades","has_bioact"),
                    ("indicacoes",   "has_ind"),
                    ("mecanismos",   "has_mec"),
                    ("artigos",      "has_articles"),
                ]
                if not status[chave]
            ]
            log.info(f"  [PARCIAL] Faltando: {', '.join(faltando)}")
            stats["parciais"] += 1
        else:
            log.info("  [NOVO]")
            stats["novos"] += 1

        # ── 1 + 2. Composto e ADMET ───────────────────────────
        # fetch_compound é necessário se: composto não existe OU admet está faltando
        needs_fetch = not status or not status["has_admet"]
        compound_data = None

        if needs_fetch:
            compound_data = fetch_compound(chembl_id)
            if not compound_data:
                log.warning(f"  Composto {chembl_id} nao encontrado na API, pulando.")
                stats["erros"] += 1
                continue

        if not status:
            # Composto novo: inserir registro e ADMET
            compound_id = upsert_compound(cur, compound_data)
            log.info(
                f"  Composto: {compound_data['name']} | "
                f"MW={compound_data['mol_weight']} | "
                f"Formula={compound_data['molecular_formula']}"
            )
            upsert_admet(cur, compound_id, compound_data.get("admet", {}))
            admet = compound_data.get("admet", {})
            log.info(
                f"  ADMET: QED={admet.get('qed_weighted') or '?'} | "
                f"aLogP={admet.get('alogp') or '?'} | "
                f"PSA={admet.get('psa') or '?'} | "
                f"Ro5={admet.get('num_ro5_violations') or 0} violacoes"
            )
        else:
            compound_id = status["id"]
            if not status["has_admet"]:
                upsert_admet(cur, compound_id, compound_data.get("admet", {}))
                log.info("  ADMET: inserido.")
            else:
                log.info("  ADMET: ja existe, pulando.")

        # ── 3. Bioatividades e alvos ──────────────────────────
        if not status or not status["has_bioact"]:
            activities       = fetch_bioactivities(chembl_id)
            targets_inserted = set()
            for act in activities:
                t_chembl = act.get("target_chembl_id")
                if not t_chembl or t_chembl in targets_inserted:
                    continue
                targets_inserted.add(t_chembl)
                target = fetch_target(t_chembl)
                if target:
                    target_id = upsert_target(cur, target)
                    insert_bioactivity(cur, compound_id, target_id, act)
                    log.info(
                        f"  Bioatividade: {act.get('type')} = "
                        f"{act.get('value')} {act.get('units')} "
                        f"-> {target['name']} ({target['organism']})"
                    )
                time.sleep(0.2)
        else:
            log.info("  Bioatividades: ja existem, pulando.")

        # ── 4. Indicações terapêuticas ────────────────────────
        if not status or not status["has_ind"]:
            indications = fetch_indications(chembl_id)
            approved    = 0
            for ind in indications:
                upsert_indication(cur, compound_id, ind)
                if (to_numeric(ind.get("max_phase_for_ind")) or 0) >= 4:
                    approved += 1
            if indications:
                log.info(
                    f"  Indicacoes: {len(indications)} total | "
                    f"{approved} aprovadas | "
                    f"ex: {indications[0].get('mesh_heading') or indications[0].get('efo_term')}"
                )
        else:
            log.info("  Indicacoes: ja existem, pulando.")

        # ── 5. Mecanismos de ação ─────────────────────────────
        if not status or not status["has_mec"]:
            mechanisms = fetch_mechanisms(chembl_id)
            for mec in mechanisms:
                t_chembl  = mec.get("target_chembl_id")
                target_id = None
                if t_chembl:
                    cur.execute(
                        "SELECT id FROM targets WHERE chembl_id = %s", (t_chembl,)
                    )
                    row = cur.fetchone()
                    if row:
                        target_id = row[0]
                upsert_mechanism(cur, compound_id, mec, target_id)
            if mechanisms:
                action_types = sorted({
                    m.get("action_type") for m in mechanisms if m.get("action_type")
                })
                log.info(
                    f"  Mecanismos: {len(mechanisms)} | "
                    f"tipos: {', '.join(action_types) or '?'}"
                )
        else:
            log.info("  Mecanismos: ja existem, pulando.")

        # ── 6. Artigos do PubMed ──────────────────────────────
        if not status or not status["has_articles"]:
            pmids    = search_pubmed(common_name)
            articles = fetch_articles(pmids)

            for article in articles:
                article_id = upsert_article(cur, article)
                link_article_compound(cur, article_id, compound_id)

                has_abstract = "abstract OK" if article["abstract"] else "sem abstract"
                n_mesh       = len(json.loads(article["mesh_terms"] or "[]") or [])
                n_kw         = len(json.loads(article["keywords"]   or "[]") or [])
                pub_types    = json.loads(article["pub_types"] or "[]") or []
                tipo         = pub_types[0] if pub_types else "?"

                log.info(
                    f"  [{article['pmid']}] {has_abstract} | "
                    f"{n_mesh} MeSH | {n_kw} keywords | {tipo}"
                )
                log.info(f"    {(article['title'] or '')[:72]}...")
                if article["abstract"]:
                    log.info(f"    {article['abstract'][:100]}...")
        else:
            log.info("  Artigos: ja existem, pulando.")

        conn.commit()
        log.info(f"  OK - {common_name} salvo.")
        time.sleep(0.5)

    cur.close()
    conn.close()

    log.info("=" * 55)
    log.info(
        f"Concluido — "
        f"novos: {stats['novos']} | "
        f"ja completos: {stats['completos']} | "
        f"parcialmente atualizados: {stats['parciais']} | "
        f"erros: {stats['erros']}"
    )


if __name__ == "__main__":
    main()