"""
backfill_abstracts.py
---------------------
Preenche abstracts, MeSH terms e keywords para artigos que foram
inseridos sem essas informacoes (versao antiga usava esummary).

Uso:
    python backfill_abstracts.py
"""

import json
import logging
import time
import xml.etree.ElementTree as ET
from typing import Optional

import psycopg2
import requests

from populate import (
    DB_CONFIG,
    PUBMED_BASE,
    _parse_abstract,
    _parse_doi,
    _parse_keywords,
    _parse_mesh_terms,
    _parse_pub_types,
    _parse_year,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

BATCH_SIZE = 20   # PubMed suporta ate ~200 IDs por request


def fetch_pmids_without_abstract(cur) -> list[tuple[str, str]]:
    """Retorna (id, pmid) dos artigos sem abstract no banco."""
    cur.execute(
        """
        SELECT id::text, pmid
        FROM   articles
        WHERE  abstract IS NULL
           OR  mesh_terms IS NULL
        ORDER  BY created_at
        """
    )
    return cur.fetchall()


def fetch_full_articles(pmids: list[str]) -> dict[str, dict]:
    """
    Busca XML completo para um lote de PMIDs.
    Retorna dicionario {pmid: dados_atualizados}.
    """
    try:
        r = requests.get(
            f"{PUBMED_BASE}/efetch.fcgi",
            params={
                "db":      "pubmed",
                "id":      ",".join(pmids),
                "retmode": "xml",
                "rettype": "abstract",
            },
            timeout=30,
        )
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except Exception as exc:
        log.error(f"Erro no efetch: {exc}")
        return {}

    result = {}
    for pub_article in root.findall(".//PubmedArticle"):
        try:
            medline    = pub_article.find("MedlineCitation")
            article_el = medline.find("Article")
            pmid       = medline.findtext("PMID")
            if not pmid:
                continue

            title_el = article_el.find("ArticleTitle")
            title    = "".join(title_el.itertext()).strip() if title_el is not None else None

            result[pmid] = {
                "title":      title,
                "abstract":   _parse_abstract(article_el),
                "doi":        _parse_doi(pub_article),
                "mesh_terms": json.dumps(_parse_mesh_terms(medline)),
                "keywords":   json.dumps(_parse_keywords(medline)),
                "pub_types":  json.dumps(_parse_pub_types(article_el)),
            }
        except Exception as exc:
            log.warning(f"  Erro ao parsear {pmid}: {exc}")
            continue

    return result


def update_article(cur, article_id: str, data: dict):
    cur.execute(
        """
        UPDATE articles SET
            title      = COALESCE(%(title)s,                  title),
            abstract   = COALESCE(%(abstract)s,               abstract),
            doi        = COALESCE(%(doi)s,                    doi),
            mesh_terms = COALESCE(%(mesh_terms)s::jsonb,      mesh_terms),
            keywords   = COALESCE(%(keywords)s::jsonb,        keywords),
            pub_types  = COALESCE(%(pub_types)s::jsonb,       pub_types)
        WHERE id = %(id)s
        """,
        {**data, "id": article_id},
    )


def main():
    log.info("Conectando ao banco...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur  = conn.cursor()

    rows = fetch_pmids_without_abstract(cur)
    total = len(rows)

    if total == 0:
        log.info("Nenhum artigo sem abstract encontrado. Banco ja esta completo.")
        cur.close()
        conn.close()
        return

    log.info(f"Encontrados {total} artigos para atualizar.")

    # Processar em lotes
    updated = 0
    for i in range(0, total, BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        id_map = {pmid: art_id for art_id, pmid in batch}   # {pmid: uuid}
        pmids  = list(id_map.keys())

        log.info(f"Lote {i // BATCH_SIZE + 1}: {len(pmids)} PMIDs...")
        fetched = fetch_full_articles(pmids)

        for pmid, data in fetched.items():
            if pmid in id_map:
                update_article(cur, id_map[pmid], data)
                has_abstract = "OK" if data["abstract"] else "--"
                n_mesh = len(json.loads(data["mesh_terms"] or "[]"))
                log.info(f"  {pmid} abstract={has_abstract} | {n_mesh} MeSH")
                updated += 1

        conn.commit()
        time.sleep(0.4)   # rate limit

    cur.close()
    conn.close()
    log.info(f"Backfill concluido: {updated}/{total} artigos atualizados.")


if __name__ == "__main__":
    main()