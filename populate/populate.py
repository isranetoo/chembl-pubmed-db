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
                        indicações, mecanismos, PubMed e ensaios clínicos
    --skip-pubmed       Pula o passo 6 (artigos do PubMed)
    --skip-trials       Pula o passo 7 (ensaios clínicos da CT.gov)
    --force             Re-processa compostos já completos (ignora o cache incremental)
"""

import argparse
import json
import logging
import time

import psycopg2

from .config import DB_CONFIG, LOG_FILE
from .chembl_client import (
    fetch_compound,
    fetch_bioactivities,
    fetch_target,
    fetch_indications,
    fetch_mechanisms,
    normalize_bioactivity,
    to_numeric,
)
from .clinicaltrials_client import sync_compound_trials
from .pubmed_client import search_pubmed, fetch_articles
from .db import (
    delete_legacy_bioactivities,
    get_compound_status,
    load_popular_compounds,
    upsert_compound,
    upsert_compound_synonyms,
    upsert_compound_atc,
    upsert_target,
    upsert_target_components,
    upsert_bioactivity,
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
        "--skip-trials",
        action="store_true",
        help="Pula o passo de ensaios clínicos (CT.gov).",
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


def _get_or_enrich_target(cur, target_chembl_id: str, cache: dict):
    """
    Resolve o UUID interno de um target, enriquecendo-o quando ainda não
    tem tax_id (sentinela da migration 0006).

    `cache` é um dict {chembl_id: uuid} usado dentro de um único composto
    para evitar requisições duplicadas — o mesmo target costuma aparecer
    em várias bioatividades.

    Retorna None se o ChEMBL não responder para esse target.
    """
    if target_chembl_id in cache:
        return cache[target_chembl_id]

    cur.execute(
        "SELECT id, (tax_id IS NOT NULL) FROM targets WHERE chembl_id = %s",
        (target_chembl_id,),
    )
    row = cur.fetchone()
    if row and row[1]:
        cache[target_chembl_id] = row[0]
        return row[0]

    target = fetch_target(target_chembl_id)
    if not target:
        return None
    target_id = upsert_target(cur, target)
    upsert_target_components(cur, target_id, target.get("components") or [])
    cache[target_chembl_id] = target_id
    return target_id


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
                ("metadata",            "has_metadata"),
                ("admet",               "has_admet"),
                ("bioatividades",       "has_bioact_enriched"),
                ("indicacoes",          "has_ind"),
                ("mecanismos",          "has_mec"),
                ("artigos",             "has_articles"),
                ("ensaios-clinicos",    "has_trials"),
                ("targets-enrich",      "has_target_enriched"),
            ]
            if not status.get(chave)
        ]
        if faltando:
            log.info(f"  [PARCIAL] Faltando: {', '.join(faltando)}")
        stats["parciais"] += 1
    elif not status:
        log.info("  [NOVO]")
        stats["novos"] += 1

    # ── 1 + 2. Composto, metadata clínico e ADMET ────────────
    #
    # `fetch_compound` retorna numa única requisição:
    #   - estrutura base (smiles, inchi, mw, fórmula)
    #   - metadata clínico (max_phase, first_approval, oral, withdrawn_*, ...)
    #   - synonyms + ATC
    #   - admet
    # Logo, basta uma chamada para cobrir metadata OU admet faltantes.
    needs_metadata = not status or not status.get("has_metadata")
    needs_admet    = not status or not status.get("has_admet")
    needs_fetch    = needs_metadata or needs_admet
    compound_data  = None

    if needs_fetch:
        compound_data = fetch_compound(chembl_id)
        if not compound_data:
            log.warning(f"  {chembl_id} nao encontrado na API, pulando.")
            stats["erros"] += 1
            return

    # Upsert do composto:
    #   - composto novo                → cria a linha
    #   - composto existente sem metadata → preenche campos NULL via COALESCE
    #   - composto existente com metadata → no-op (only `name` é re-escrito)
    if compound_data is not None:
        compound_id = upsert_compound(cur, compound_data)
    else:
        compound_id = status["id"]

    # ── Metadata: synonyms + ATC ──────────────────────────────
    if needs_metadata and compound_data is not None:
        n_syn = upsert_compound_synonyms(cur, compound_id, compound_data.get("synonyms") or [])
        n_atc = upsert_compound_atc     (cur, compound_id, compound_data.get("atc")      or [])
        log.info(
            f"  Metadata: {compound_data['name']} | "
            f"type={compound_data.get('molecule_type') or '?'} | "
            f"phase={compound_data.get('max_phase') if compound_data.get('max_phase') is not None else '?'} | "
            f"first_approval={compound_data.get('first_approval') or '?'} | "
            f"synonyms=+{n_syn} | atc=+{n_atc}"
        )
    else:
        log.info("  Metadata: ja existe, pulando.")

    # ── ADMET ─────────────────────────────────────────────────
    if needs_admet and compound_data is not None:
        upsert_admet(cur, compound_id, compound_data.get("admet", {}))
        admet = compound_data.get("admet", {})
        log.info(
            f"  ADMET: QED={admet.get('qed_weighted') or '?'} | "
            f"aLogP={admet.get('alogp') or '?'} | "
            f"PSA={admet.get('psa') or '?'} | "
            f"Ro5={admet.get('num_ro5_violations') or 0} violacoes"
        )
    else:
        log.info("  ADMET: ja existe, pulando.")

    # ── 3. Bioatividades e alvos ──────────────────────────────
    #
    # Duas situações disparam re-fetch:
    #   (a) compound novo, sem nenhuma linha em bioactivities
    #   (b) compound legado: tem linhas mas todas com assay_type=NULL,
    #       inseridas antes da migration 0005. Apagamos as legadas para
    #       que o INSERT enriquecido grave os campos novos.
    needs_bioact = (
        not status
        or not status.get("has_bioact")
        or not status.get("has_bioact_enriched")
    )
    if "bioact" in skip:
        log.info("  Bioatividades: ignoradas (--only-compounds).")
    elif needs_bioact:
        # Limpa linhas legadas (sem assay_type) — preserva linhas já
        # enriquecidas; o UPSERT cuidará dessas via activity_id.
        n_removed = delete_legacy_bioactivities(cur, compound_id)
        if n_removed:
            log.info(f"  Bioatividades legadas removidas: {n_removed}")

        activities    = fetch_bioactivities(chembl_id)
        target_cache  = {}    # chembl_id → uuid, escopo do composto
        n_inserted    = 0
        for raw_act in activities:
            t_chembl = raw_act.get("target_chembl_id")
            if not t_chembl:
                continue
            # _get_or_enrich_target resolve+enriquece o target (1 chamada
            # por target distinto, graças ao cache). Targets que já têm
            # tax_id no banco viram um SELECT puro.
            target_id = _get_or_enrich_target(cur, t_chembl, target_cache)
            if not target_id:
                continue

            act = normalize_bioactivity(raw_act)
            upsert_bioactivity(cur, compound_id, target_id, act)
            n_inserted += 1

            log.info(
                f"  Bioatividade: {act.get('type')} = "
                f"{act.get('standard_value') or act.get('value')} "
                f"{act.get('standard_units') or act.get('units')} | "
                f"pChEMBL={act.get('pchembl_value') or '?'} | "
                f"assay={act.get('assay_type') or '?'} | "
                f"-> {raw_act.get('target_pref_name')} "
                f"({act.get('target_organism') or '?'})"
            )
        log.info(f"  Bioatividades: {n_inserted} inseridas/atualizadas.")
    else:
        log.info("  Bioatividades: ja existem (enriquecidas), pulando.")

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
        mechanisms   = fetch_mechanisms(chembl_id)
        target_cache = {}    # reaproveitado pra mechanisms; cache local
        n_variants   = 0
        for mec in mechanisms:
            t_chembl  = mec.get("target_chembl_id")
            target_id = _get_or_enrich_target(cur, t_chembl, target_cache) if t_chembl else None
            upsert_mechanism(cur, compound_id, mec, target_id)
            if mec.get("variant_sequence"):
                n_variants += 1
        if mechanisms:
            action_types = sorted({
                m.get("action_type") for m in mechanisms if m.get("action_type")
            })
            log.info(
                f"  Mecanismos: {len(mechanisms)} | "
                f"tipos: {', '.join(action_types) or '?'}"
                + (f" | variants: {n_variants}" if n_variants else "")
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

    # ── 7. Ensaios clínicos (ClinicalTrials.gov v2) ───────────
    #
    # `sync_compound_trials` faz fetch + upsert na tabela clinical_trials
    # e cria links em compound_clinical_trials. Caller controla commit.
    # Sentinela: tem ao menos 1 linha em compound_clinical_trials para
    # esse chembl_id (mesma semântica do `--skip-synced` do script
    # populate_clinical_trials.py).
    if "trials" in skip:
        log.info("  Ensaios clinicos: ignorados (--skip-trials / --only-compounds).")
    elif not status or not status.get("has_trials"):
        try:
            trial_name = _get_pubmed_name(cur, compound_id, display_name)
            result = sync_compound_trials(cur, chembl_id, trial_name)
            log.info(
                f"  Ensaios clinicos: fetched={result['trials_fetched']} | "
                f"upserted={result['trials_upserted']} | "
                f"links={result['links_created']}"
            )
        except Exception as exc:
            # CT.gov é externa e instável — não derruba o pipeline,
            # só loga e segue. Erro do compound inteiro é tratado no main().
            log.warning(f"  Ensaios clinicos: falha na CT.gov ({exc}); seguindo.")
    else:
        log.info("  Ensaios clinicos: ja existem, pulando.")

    # ── 8. Enrichment de alvos (legados) ─────────────────────
    #
    # Compostos antigos têm targets gravados ANTES da migration 0006
    # (sem tax_id, components, xrefs). Aqui listamos esses targets e
    # enriquecemos um por um. Re-execuções idempotentes.
    if "targets_enrich" in skip:
        log.info("  Targets enrichment: ignorado (--only-compounds).")
    elif not status or not status.get("has_target_enriched"):
        cur.execute(
            """
            SELECT DISTINCT t.chembl_id
            FROM (
                SELECT target_id FROM bioactivities
                WHERE compound_id = %s AND target_id IS NOT NULL
                UNION
                SELECT target_id FROM mechanisms
                WHERE compound_id = %s AND target_id IS NOT NULL
            ) used
            JOIN targets t ON t.id = used.target_id
            WHERE t.tax_id IS NULL
            ORDER BY t.chembl_id
            """,
            (compound_id, compound_id),
        )
        pendentes = [r[0] for r in cur.fetchall()]
        if pendentes:
            cache = {}
            n_ok = 0
            for t_chembl in pendentes:
                if _get_or_enrich_target(cur, t_chembl, cache):
                    n_ok += 1
                time.sleep(0.15)
            log.info(f"  Targets enrichment: {n_ok}/{len(pendentes)} alvos enriquecidos.")
        else:
            # Não há targets, ou todos já estão enriquecidos (e o status
            # ficou stale por algum motivo — improvável). Apenas loga.
            log.info("  Targets enrichment: nenhum alvo pendente.")
    else:
        log.info("  Targets enrichment: ja existe, pulando.")


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
        # Lê da tabela seed_compounds (migration 0002_seed_compounds).
        compounds = list(load_popular_compounds())

    # --add sempre acrescenta (independente de --only)
    for cid in args.add:
        cid = cid.upper()
        if cid not in {c for c, _ in compounds}:
            compounds.append((cid, cid))  # nome = ID até fetch_compound retornar o real

    # ── Montar conjunto de etapas a pular ─────────────────────
    skip: set = set()
    if args.only_compounds:
        skip = {"bioact", "ind", "mec", "pubmed", "trials", "targets_enrich"}
    if args.skip_pubmed:
        skip.add("pubmed")
    if args.skip_trials:
        skip.add("trials")

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