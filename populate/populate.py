"""
populate.py
-----------
Ponto de entrada principal com suporte a CLI via argparse.

Uso básico:
    python populate.py

Exemplos com flags:
    python populate.py --add CHEMBL941
    python populate.py --add CHEMBL941 --add CHEMBL192
    python populate.py --only CHEMBL25 --only CHEMBL521
    python populate.py --only-compounds
    python populate.py --skip-pubmed
    python populate.py --force
    python populate.py --add CHEMBL941 --skip-pubmed --force

Flags:
    --add  CHEMBL_ID    Adiciona um composto extra à execução (repetível)
    --only CHEMBL_ID    Executa somente estes IDs, substituindo a lista padrão (repetível)
    --only-compounds    Roda só os passos 1+2 (estrutura e ADMET); pula bioatividades,
                        indicações, mecanismos e PubMed
    --skip-pubmed       Pula o passo 6 (artigos do PubMed)
    --force             Re-processa compostos já completos (ignora o cache incremental)
"""

import argparse
import json
import logging
import time

import psycopg2

from config import DB_CONFIG, POPULAR_COMPOUNDS, LOG_FILE
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


# ============================================================
# CLI
# ============================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="populate.py",
        description="Popula o banco ChEMBL+PubMed com compostos farmacológicos.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
exemplos:
  python populate.py
  python populate.py --add CHEMBL941
  python populate.py --only CHEMBL25 --only CHEMBL521
  python populate.py --only-compounds --force
  python populate.py --skip-pubmed --add CHEMBL941
        """,
    )

    parser.add_argument(
        "--add",
        metavar="CHEMBL_ID",
        action="append",
        default=[],
        help="Adiciona um ChEMBL ID extra à execução (pode repetir: --add X --add Y).",
    )
    parser.add_argument(
        "--only",
        metavar="CHEMBL_ID",
        action="append",
        default=[],
        help="Executa somente estes IDs, substituindo a lista padrão (pode repetir).",
    )
    parser.add_argument(
        "--only-compounds",
        action="store_true",
        help="Roda só estrutura + ADMET. Pula bioatividades, indicações, mecanismos e PubMed.",
    )
    parser.add_argument(
        "--skip-pubmed",
        action="store_true",
        help="Pula o passo de artigos do PubMed.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-processa compostos já completos (ignora o cache incremental).",
    )

    return parser.parse_args()


# ============================================================
# Lógica de um único composto
# ============================================================

def _get_pubmed_name(cur, compound_id: str, fallback: str) -> str:
    """Retorna o nome do composto no banco, ou o fallback se não encontrar."""
    cur.execute("SELECT name FROM compounds WHERE id = %s", (compound_id,))
    row = cur.fetchone()
    return row[0] if row else fallback


def process_compound(
    chembl_id:    str,
    display_name: str,
    cur,
    skip:         set,   # conjunto de etapas a pular: "bioact"|"ind"|"mec"|"pubmed"
    force:        bool,
    stats:        dict,
) -> None:
    """
    Processa um composto completo: busca nas APIs e persiste no banco.

    Parâmetros
    ----------
    chembl_id    : ID do ChEMBL (ex: "CHEMBL25")
    display_name : nome para log (ex: "Aspirin"); para --add, é o próprio ID
    cur          : cursor psycopg2 ativo
    skip         : etapas a ignorar {"bioact", "ind", "mec", "pubmed"}
    force        : se True, ignora cache incremental e re-processa tudo
    stats        : dict de contadores atualizado in-place
    """
    log.info("=" * 55)
    log.info(f"Processando: {display_name} ({chembl_id})")

    # ── Status incremental ────────────────────────────────────
    status = get_compound_status(cur, chembl_id)

    if not force and status and status["is_complete"]:
        log.info("  Ja completo — pulando. (use --force para re-processar)")
        stats["completos"] += 1
        return

    if force and status and status["is_complete"]:
        log.info("  [FORCE] Re-processando composto completo.")
        # Zera os flags de status para forçar re-fetch de todas as etapas
        status = {k: False for k in status}
        status["id"] = get_compound_status(cur, chembl_id)["id"]

    if status and not status.get("is_complete", False):
        faltando = [
            etapa for etapa, chave in [
                ("admet",         "has_admet"),
                ("bioatividades", "has_bioact"),
                ("indicacoes",    "has_ind"),
                ("mecanismos",    "has_mec"),
                ("artigos",       "has_articles"),
            ]
            if not status.get(chave)
        ]
        if faltando:
            log.info(f"  [PARCIAL] Faltando: {', '.join(faltando)}")
        stats["parciais"] += 1
    elif not status:
        log.info("  [NOVO]")
        stats["novos"] += 1

    # ── 1 + 2. Composto e ADMET ───────────────────────────────
    needs_fetch   = not status or not status.get("has_admet")
    compound_data = None

    if needs_fetch:
        compound_data = fetch_compound(chembl_id)
        if not compound_data:
            log.warning(f"  {chembl_id} nao encontrado na API, pulando.")
            stats["erros"] += 1
            return

    if not status or not status.get("id"):
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
        if not status.get("has_admet"):
            upsert_admet(cur, compound_id, compound_data.get("admet", {}))
            log.info("  ADMET: inserido.")
        else:
            log.info("  ADMET: ja existe, pulando.")

    # ── 3. Bioatividades e alvos ──────────────────────────────
    if "bioact" in skip:
        log.info("  Bioatividades: ignoradas (--only-compounds).")
    elif not status or not status.get("has_bioact"):
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

    # ── 4. Indicações terapêuticas ────────────────────────────
    if "ind" in skip:
        log.info("  Indicacoes: ignoradas (--only-compounds).")
    elif not status or not status.get("has_ind"):
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

    # ── 5. Mecanismos de ação ─────────────────────────────────
    if "mec" in skip:
        log.info("  Mecanismos: ignorados (--only-compounds).")
    elif not status or not status.get("has_mec"):
        mechanisms = fetch_mechanisms(chembl_id)
        for mec in mechanisms:
            t_chembl  = mec.get("target_chembl_id")
            target_id = None
            if t_chembl:
                cur.execute("SELECT id FROM targets WHERE chembl_id = %s", (t_chembl,))
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

    # ── 6. Artigos do PubMed ──────────────────────────────────
    if "pubmed" in skip:
        log.info("  Artigos: ignorados (--skip-pubmed / --only-compounds).")
    elif not status or not status.get("has_articles"):
        pubmed_name = _get_pubmed_name(cur, compound_id, display_name)
        pmids       = search_pubmed(pubmed_name)
        articles    = fetch_articles(pmids)

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


# ============================================================
# Main
# ============================================================

def main():
    args = parse_args()

    # ── Montar lista de compostos ─────────────────────────────
    if args.only:
        # --only substitui a lista padrão; --add ainda acrescenta extras
        compounds = [(cid.upper(), cid.upper()) for cid in args.only]
    else:
        compounds = list(POPULAR_COMPOUNDS)

    # --add sempre acrescenta (independente de --only)
    for cid in args.add:
        cid = cid.upper()
        if cid not in {c for c, _ in compounds}:
            compounds.append((cid, cid))  # nome = ID até fetch_compound retornar o real

    # ── Montar conjunto de etapas a pular ─────────────────────
    skip: set = set()
    if args.only_compounds:
        skip = {"bioact", "ind", "mec", "pubmed"}
    if args.skip_pubmed:
        skip.add("pubmed")

    # ── Log do que vai rodar ──────────────────────────────────
    log.info(f"Log salvo em: {LOG_FILE}")
    log.info(f"Compostos: {len(compounds)}")
    if skip:
        log.info(f"Etapas ignoradas: {', '.join(sorted(skip))}")
    if args.force:
        log.info("Modo FORCE ativo — compostos completos serao re-processados.")

    # ── Conectar ao banco ─────────────────────────────────────
    log.info("Conectando ao banco de dados...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur  = conn.cursor()

    stats = {"novos": 0, "completos": 0, "parciais": 0, "erros": 0}

    for chembl_id, display_name in compounds:
        try:
            process_compound(
                chembl_id    = chembl_id,
                display_name = display_name,
                cur          = cur,
                skip         = skip,
                force        = args.force,
                stats        = stats,
            )
            conn.commit()
            time.sleep(0.5)
        except Exception as exc:
            log.error(f"Erro inesperado em {chembl_id}: {exc}")
            conn.rollback()
            stats["erros"] += 1

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