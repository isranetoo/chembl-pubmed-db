"""
pubmed_client.py
----------------
Busca de artigos no PubMed e parsing completo do XML (efetch).

Fluxo:
  1. search_pubmed()   — esearch  → lista de PMIDs
  2. fetch_articles()  — efetch   → XML completo com abstract, MeSH, keywords
"""

import json
import logging
import xml.etree.ElementTree as ET
from typing import Optional

import requests

from config import PUBMED_BASE, MAX_ARTICLES
from http_retry import get_with_retry

log = logging.getLogger(__name__)


# ============================================================
# Busca de IDs
# ============================================================

def search_pubmed(compound_name: str) -> list:
    """Retorna lista de PMIDs para o nome do composto."""
    try:
        r = get_with_retry(
            f"{PUBMED_BASE}/esearch.fcgi",
            params={
                "db":      "pubmed",
                "term":    f"{compound_name}[Title/Abstract]",
                "retmax":  MAX_ARTICLES,
                "retmode": "json",
            },
            timeout=20,
        )
        return r.json().get("esearchresult", {}).get("idlist", [])
    except Exception as exc:
        log.error(f"Erro ao buscar PubMed para '{compound_name}': {exc}")
        return []


# ============================================================
# Helpers de parsing XML
# ============================================================

def _parse_abstract(article_elem: ET.Element) -> Optional[str]:
    """
    Extrai o abstract de <Article>.

    Formatos suportados:
      Simples      — <AbstractText>Texto corrido</AbstractText>
      Estruturado  — <AbstractText Label="BACKGROUND">...</AbstractText>
                     <AbstractText Label="METHODS">...</AbstractText>

    itertext() captura texto mesmo com tags inline <b>, <i>, <sub>, <sup>.
    Seções "UNLABELLED" são tratadas como texto simples.
    """
    abstract_el = article_elem.find("Abstract")
    if abstract_el is None:
        return None

    sections = []
    for at in abstract_el.findall("AbstractText"):
        text = "".join(at.itertext()).strip()
        if not text:
            continue
        label = at.get("Label") or at.get("NlmCategory", "")
        if label and label.upper() not in ("UNLABELLED", ""):
            sections.append(f"{label.capitalize()}: {text}")
        else:
            sections.append(text)

    if not sections:
        return None
    return "\n\n".join(sections) if len(sections) > 1 else sections[0]


def _parse_year(article_elem: ET.Element) -> Optional[int]:
    """
    Extrai o ano de <PubDate>.
    Suporta <Year>2023</Year> e <MedlineDate>2023 Jan-Feb</MedlineDate>.
    """
    pub_date = article_elem.find(".//PubDate")
    if pub_date is None:
        return None
    year_text = pub_date.findtext("Year")
    if year_text:
        try:
            return int(year_text)
        except ValueError:
            pass
    medline = pub_date.findtext("MedlineDate", "")
    try:
        return int(medline.split()[0])
    except (ValueError, IndexError):
        return None


def _parse_doi(pubmed_article: ET.Element) -> Optional[str]:
    """
    Procura DOI em dois lugares:
      1. <ELocationID EIdType="doi"> em <Article>
      2. <ArticleId IdType="doi"> em <PubmedData>
    """
    for eid in pubmed_article.findall(".//ELocationID"):
        if eid.get("EIdType", "").lower() == "doi":
            return (eid.text or "").strip() or None
    for aid in pubmed_article.findall(".//ArticleId"):
        if aid.get("IdType", "").lower() == "doi":
            return (aid.text or "").strip() or None
    return None


def _parse_mesh_terms(medline_elem: ET.Element) -> Optional[list]:
    """
    Extrai termos MeSH de <MeshHeadingList>.
    Retorna lista de dicts: {"term": str, "major": bool}

    Exemplo de uso no banco:
      SELECT title FROM articles
      WHERE mesh_terms @> '[{"term": "Anti-Inflammatory Agents"}]';
    """
    terms = []
    for heading in medline_elem.findall(".//MeshHeading"):
        descriptor = heading.find("DescriptorName")
        if descriptor is not None and descriptor.text:
            terms.append({
                "term":  descriptor.text.strip(),
                "major": descriptor.get("MajorTopicYN", "N") == "Y",
            })
    return terms if terms else None


def _parse_keywords(medline_elem: ET.Element) -> Optional[list]:
    """
    Extrai palavras-chave dos autores de <KeywordList>.

    Exemplo:
      SELECT title FROM articles WHERE keywords @> '["inflammation"]';
    """
    kws = [
        kw.text.strip()
        for kw in medline_elem.findall(".//Keyword")
        if kw.text
    ]
    return kws if kws else None


def _parse_pub_types(article_elem: ET.Element) -> Optional[list]:
    """
    Extrai tipos de publicação de <PublicationTypeList>.
    Ex: ["Journal Article", "Review", "Clinical Trial", "Meta-Analysis"]
    """
    types = [
        pt.text.strip()
        for pt in article_elem.findall(".//PublicationType")
        if pt.text
    ]
    return types if types else None


# ============================================================
# Fetch principal
# ============================================================

def fetch_articles(pmids: list) -> list:
    """
    Busca artigos completos via efetch (XML), extraindo:
      - título, abstract (simples ou estruturado)
      - autores, periódico, ano, DOI
      - termos MeSH, palavras-chave, tipos de publicação

    Por que efetch e não esummary?
      esearch  → só IDs
      esummary → metadados sem abstract
      efetch   → XML completo (único que tem abstract)
    """
    if not pmids:
        return []

    try:
        r = get_with_retry(
            f"{PUBMED_BASE}/efetch.fcgi",
            params={
                "db":      "pubmed",
                "id":      ",".join(pmids),
                "retmode": "xml",
                "rettype": "abstract",
            },
            timeout=30,
        )
        root = ET.fromstring(r.content)
    except ET.ParseError as exc:
        log.error(f"Erro ao parsear XML do PubMed: {exc}")
        return []
    except Exception as exc:
        log.error(f"Erro na requisicao efetch: {exc}")
        return []

    articles = []

    for pub_article in root.findall(".//PubmedArticle"):
        try:
            medline    = pub_article.find("MedlineCitation")
            article_el = medline.find("Article")

            pmid = medline.findtext("PMID")
            if not pmid:
                continue

            title_el = article_el.find("ArticleTitle")
            title = "".join(title_el.itertext()).strip() if title_el is not None else None

            authors = []
            author_list = article_el.find("AuthorList")
            if author_list is not None:
                for author in author_list.findall("Author"):
                    collective = author.findtext("CollectiveName")
                    if collective:
                        authors.append(collective.strip())
                    else:
                        last = author.findtext("LastName", "")
                        fore = author.findtext("ForeName", "")
                        name = f"{fore} {last}".strip()
                        if name:
                            authors.append(name)

            journal    = None
            journal_el = article_el.find("Journal")
            if journal_el is not None:
                journal = (
                    journal_el.findtext("Title")
                    or journal_el.findtext("ISOAbbreviation")
                )

            articles.append({
                "pmid":       pmid,
                "title":      title,
                "abstract":   _parse_abstract(article_el),
                "authors":    json.dumps(authors),
                "journal":    journal,
                "pub_year":   _parse_year(article_el),
                "doi":        _parse_doi(pub_article),
                "mesh_terms": json.dumps(_parse_mesh_terms(medline)),
                "keywords":   json.dumps(_parse_keywords(medline)),
                "pub_types":  json.dumps(_parse_pub_types(article_el)),
            })

        except Exception as exc:
            log.warning(f"  Artigo ignorado por erro de parsing: {exc}")
            continue

    with_abstract = sum(1 for a in articles if a["abstract"])
    log.info(
        f"  efetch: {len(articles)}/{len(pmids)} artigos parseados | "
        f"{with_abstract} com abstract"
    )
    return articles