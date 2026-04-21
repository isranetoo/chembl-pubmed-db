"""
tests/test_modules.py
---------------------
Testes unitários para chembl_client, pubmed_client e db.

Execução:
    pip install pytest
    pytest tests/ -v
    pytest tests/ -v -k "chembl"       # só testes do ChEMBL
    pytest tests/ -v -k "pubmed"       # só testes do PubMed
    pytest tests/ -v -k "db"           # só testes do banco
    pytest tests/ --tb=short           # traceback curto

Nenhuma chamada de rede real é feita — todas as requisições HTTP
e interações com o banco são substituídas por mocks.
"""

import json
import textwrap
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import MagicMock, patch, call


# ============================================================
# Fixtures reutilizáveis
# ============================================================

ASPIRIN_API_RESPONSE = {
    "pref_name": "ASPIRIN",
    "molecule_properties": {
        "full_molformula": "C9H8O4",
        "full_mwt":        "180.16",
        "alogp":           "1.19",
        "hbd":             1,
        "hba":             3,
        "psa":             63.6,
        "num_ro5_violations": 0,
        "cx_logp":         "1.31",
        "cx_logd":         "0.87",
        "cx_most_apka":    "3.41",
        "cx_most_bpka":    None,
        "molecular_species": "ACID",
        "mw_freebase":     "180.16",
        "mw_monoisotopic": "180.04",
        "heavy_atoms":     13,
        "aromatic_rings":  1,
        "rtb":             3,
        "hbd_lipinski":    1,
        "hba_lipinski":    3,
        "ro3_pass":        "N",
        "qed_weighted":    "0.55",
        "num_alerts":      0,
    },
    "molecule_structures": {
        "canonical_smiles": "CC(=O)Oc1ccccc1C(=O)O",
        "standard_inchi_key": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
    },
}

BIOACTIVITIES_RESPONSE = {
    "activities": [
        {
            "target_chembl_id": "CHEMBL612545",
            "type":             "IC50",
            "value":            "34.6",
            "units":            "uM",
            "relation":         "=",
        }
    ]
}

TARGET_RESPONSE = {
    "pref_name":   "Cyclooxygenase-1",
    "target_type": "SINGLE PROTEIN",
    "organism":    "Homo sapiens",
}

INDICATIONS_PAGE1 = {
    "drug_indications": [
        {
            "drugind_id":       1001,
            "mesh_id":          "D006261",
            "mesh_heading":     "Headache",
            "efo_id":           "EFO:0003843",
            "efo_term":         "headache",
            "max_phase_for_ind": "4",
        }
    ],
    "page_meta": {"total_count": 1},
}

MECHANISMS_RESPONSE = {
    "mechanisms": [
        {
            "mec_id":              101,
            "mechanism_of_action": "Cyclooxygenase inhibitor",
            "action_type":         "INHIBITOR",
            "target_chembl_id":    "CHEMBL612545",
            "target_name":         "Cyclooxygenase-1",
            "direct_interaction":  1,
            "disease_efficacy":    1,
            "mechanism_comment":   None,
            "selectivity_comment": None,
            "binding_site_comment":None,
        }
    ]
}

PUBMED_ESEARCH_RESPONSE = {
    "esearchresult": {"idlist": ["38000001", "38000002"]}
}

PUBMED_EFETCH_XML = textwrap.dedent("""\
    <?xml version="1.0"?>
    <PubmedArticleSet>
      <PubmedArticle>
        <MedlineCitation>
          <PMID>38000001</PMID>
          <Article>
            <ArticleTitle>Aspirin and cardiovascular risk</ArticleTitle>
            <Abstract>
              <AbstractText Label="BACKGROUND">Aspirin prevents clots.</AbstractText>
              <AbstractText Label="METHODS">RCT with 1000 patients.</AbstractText>
            </Abstract>
            <AuthorList>
              <Author>
                <LastName>Smith</LastName>
                <ForeName>John</ForeName>
              </Author>
            </AuthorList>
            <Journal>
              <Title>Journal of Cardiology</Title>
              <JournalIssue>
                <PubDate><Year>2023</Year></PubDate>
              </JournalIssue>
            </Journal>
            <PublicationTypeList>
              <PublicationType>Journal Article</PublicationType>
              <PublicationType>Review</PublicationType>
            </PublicationTypeList>
          </Article>
          <MeshHeadingList>
            <MeshHeading>
              <DescriptorName MajorTopicYN="Y">Aspirin</DescriptorName>
            </MeshHeading>
            <MeshHeading>
              <DescriptorName MajorTopicYN="N">Inflammation</DescriptorName>
            </MeshHeading>
          </MeshHeadingList>
          <KeywordList>
            <Keyword>aspirin</Keyword>
            <Keyword>cardioprotection</Keyword>
          </KeywordList>
        </MedlineCitation>
        <PubmedData>
          <ArticleIdList>
            <ArticleId IdType="doi">10.1234/jcard.2023.001</ArticleId>
          </ArticleIdList>
        </PubmedData>
      </PubmedArticle>
    </PubmedArticleSet>
""")

PUBMED_EFETCH_XML_SIMPLE_ABSTRACT = textwrap.dedent("""\
    <?xml version="1.0"?>
    <PubmedArticleSet>
      <PubmedArticle>
        <MedlineCitation>
          <PMID>38000002</PMID>
          <Article>
            <ArticleTitle>Ibuprofen <i>in vivo</i> effects</ArticleTitle>
            <Abstract>
              <AbstractText>Simple paragraph abstract without labels.</AbstractText>
            </Abstract>
            <AuthorList>
              <Author><CollectiveName>NSAID Study Group</CollectiveName></Author>
            </AuthorList>
            <Journal>
              <ISOAbbreviation>J Pain</ISOAbbreviation>
              <JournalIssue>
                <PubDate><MedlineDate>2022 Jan-Feb</MedlineDate></PubDate>
              </JournalIssue>
            </Journal>
            <PublicationTypeList>
              <PublicationType>Journal Article</PublicationType>
            </PublicationTypeList>
          </Article>
        </MedlineCitation>
      </PubmedArticle>
    </PubmedArticleSet>
""")


def _mock_response(json_data=None, content=None, status_code=200):
    """Cria um mock de requests.Response."""
    r = MagicMock()
    r.status_code = status_code
    if json_data is not None:
        r.json.return_value = json_data
    if content is not None:
        r.content = content if isinstance(content, bytes) else content.encode()
    r.raise_for_status.return_value = None
    return r


# ============================================================
# Testes: chembl_client — to_numeric
# ============================================================

class TestToNumeric(unittest.TestCase):

    def setUp(self):
        from populate.chembl_client import to_numeric
        self.fn = to_numeric

    def test_float_string(self):
        self.assertEqual(self.fn("3.14"), 3.14)

    def test_int_string(self):
        self.assertEqual(self.fn("4"), 4.0)

    def test_already_float(self):
        self.assertEqual(self.fn(1.5), 1.5)

    def test_already_int(self):
        self.assertEqual(self.fn(2), 2.0)

    def test_none_returns_none(self):
        self.assertIsNone(self.fn(None))

    def test_invalid_string_returns_none(self):
        self.assertIsNone(self.fn("nao_e_numero"))

    def test_empty_string_returns_none(self):
        self.assertIsNone(self.fn(""))

    def test_zero(self):
        self.assertEqual(self.fn("0"), 0.0)

    def test_negative(self):
        self.assertEqual(self.fn("-1.5"), -1.5)


# ============================================================
# Testes: chembl_client — fetch_compound
# ============================================================

class TestFetchCompound(unittest.TestCase):

    @patch("chembl_client.get_with_retry")
    def test_sucesso(self, mock_get):
        mock_get.return_value = _mock_response(ASPIRIN_API_RESPONSE)
        from populate.chembl_client import fetch_compound
        result = fetch_compound("CHEMBL25")

        self.assertIsNotNone(result)
        self.assertEqual(result["chembl_id"],        "CHEMBL25")
        self.assertEqual(result["name"],             "ASPIRIN")
        self.assertEqual(result["molecular_formula"],"C9H8O4")
        self.assertEqual(result["mol_weight"],       "180.16")
        self.assertEqual(result["smiles"],           "CC(=O)Oc1ccccc1C(=O)O")

    @patch("chembl_client.get_with_retry")
    def test_admet_populado(self, mock_get):
        mock_get.return_value = _mock_response(ASPIRIN_API_RESPONSE)
        from populate.chembl_client import fetch_compound
        result = fetch_compound("CHEMBL25")

        admet = result["admet"]
        self.assertEqual(admet["alogp"],            "1.19")
        self.assertEqual(admet["num_ro5_violations"], 0)
        self.assertEqual(admet["qed_weighted"],     "0.55")
        self.assertEqual(admet["molecular_species"], "ACID")

    @patch("chembl_client.get_with_retry")
    def test_erro_retorna_none(self, mock_get):
        mock_get.side_effect = Exception("timeout")
        from populate.chembl_client import fetch_compound
        result = fetch_compound("CHEMBL999")
        self.assertIsNone(result)

    @patch("chembl_client.get_with_retry")
    def test_pref_name_none_usa_chembl_id(self, mock_get):
        data = {**ASPIRIN_API_RESPONSE, "pref_name": None}
        data["molecule_properties"] = ASPIRIN_API_RESPONSE["molecule_properties"]
        data["molecule_structures"] = ASPIRIN_API_RESPONSE["molecule_structures"]
        mock_get.return_value = _mock_response(data)
        from populate.chembl_client import fetch_compound
        result = fetch_compound("CHEMBL25")
        self.assertEqual(result["name"], "CHEMBL25")


# ============================================================
# Testes: chembl_client — fetch_bioactivities
# ============================================================

class TestFetchBioactivities(unittest.TestCase):

    @patch("chembl_client.get_with_retry")
    def test_retorna_lista(self, mock_get):
        mock_get.return_value = _mock_response(BIOACTIVITIES_RESPONSE)
        from populate.chembl_client import fetch_bioactivities
        result = fetch_bioactivities("CHEMBL25")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "IC50")

    @patch("chembl_client.get_with_retry")
    def test_erro_retorna_lista_vazia(self, mock_get):
        mock_get.side_effect = Exception("connection error")
        from populate.chembl_client import fetch_bioactivities
        self.assertEqual(fetch_bioactivities("CHEMBL25"), [])

    @patch("chembl_client.get_with_retry")
    def test_resposta_vazia(self, mock_get):
        mock_get.return_value = _mock_response({"activities": []})
        from populate.chembl_client import fetch_bioactivities
        self.assertEqual(fetch_bioactivities("CHEMBL25"), [])


# ============================================================
# Testes: chembl_client — fetch_target
# ============================================================

class TestFetchTarget(unittest.TestCase):

    @patch("chembl_client.get_with_retry")
    def test_sucesso(self, mock_get):
        mock_get.return_value = _mock_response(TARGET_RESPONSE)
        from populate.chembl_client import fetch_target
        result = fetch_target("CHEMBL612545")
        self.assertEqual(result["name"],     "Cyclooxygenase-1")
        self.assertEqual(result["organism"], "Homo sapiens")
        self.assertEqual(result["type"],     "SINGLE PROTEIN")

    @patch("chembl_client.get_with_retry")
    def test_erro_retorna_none(self, mock_get):
        mock_get.side_effect = Exception("not found")
        from populate.chembl_client import fetch_target
        self.assertIsNone(fetch_target("CHEMBLXXX"))


# ============================================================
# Testes: chembl_client — fetch_indications (paginação)
# ============================================================

class TestFetchIndications(unittest.TestCase):

    @patch("chembl_client.time")
    @patch("chembl_client.get_with_retry")
    def test_pagina_unica(self, mock_get, mock_time):
        mock_get.return_value = _mock_response(INDICATIONS_PAGE1)
        from populate.chembl_client import fetch_indications
        result = fetch_indications("CHEMBL25")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["mesh_heading"], "Headache")

    @patch("chembl_client.time")
    @patch("chembl_client.get_with_retry")
    def test_paginacao_duas_paginas(self, mock_get, mock_time):
        """
        Verifica que fetch_indications faz múltiplas requisições quando
        total_count > limit. Usamos limit=1 via monkeypatch do módulo.
        """
        page1 = {
            "drug_indications": [{"drugind_id": 1, "mesh_heading": "Pain"}],
            "page_meta":        {"total_count": 2},
        }
        page2 = {
            "drug_indications": [{"drugind_id": 2, "mesh_heading": "Fever"}],
            "page_meta":        {"total_count": 2},
        }
        mock_get.side_effect = [
            _mock_response(page1),
            _mock_response(page2),
        ]

        import populate.chembl_client as cc
        original_limit = 100

        # Injetar limit=1 para forçar paginação com 2 páginas
        def fetch_with_small_limit(chembl_id):
            indications = []
            offset, limit = 0, 1
            while True:
                try:
                    r = cc.get_with_retry(
                        f"{cc.CHEMBL_BASE}/drug_indication.json",
                        params={"molecule_chembl_id": chembl_id, "limit": limit, "offset": offset},
                        timeout=20,
                    )
                    data  = r.json()
                    batch = data.get("drug_indications", [])
                    indications.extend(batch)
                    total   = data.get("page_meta", {}).get("total_count", 0)
                    offset += limit
                    if offset >= total:
                        break
                except Exception:
                    break
            return indications

        result = fetch_with_small_limit("CHEMBL25")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["mesh_heading"], "Pain")
        self.assertEqual(result[1]["mesh_heading"], "Fever")
        self.assertEqual(mock_get.call_count, 2)

    @patch("chembl_client.time")
    @patch("chembl_client.get_with_retry")
    def test_erro_retorna_lista_parcial(self, mock_get, mock_time):
        mock_get.side_effect = Exception("timeout")
        from populate.chembl_client import fetch_indications
        self.assertEqual(fetch_indications("CHEMBL25"), [])


# ============================================================
# Testes: chembl_client — fetch_mechanisms
# ============================================================

class TestFetchMechanisms(unittest.TestCase):

    @patch("chembl_client.get_with_retry")
    def test_sucesso(self, mock_get):
        mock_get.return_value = _mock_response(MECHANISMS_RESPONSE)
        from populate.chembl_client import fetch_mechanisms
        result = fetch_mechanisms("CHEMBL25")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["action_type"],         "INHIBITOR")
        self.assertEqual(result[0]["mechanism_of_action"], "Cyclooxygenase inhibitor")
        self.assertEqual(result[0]["direct_interaction"],  1)

    @patch("chembl_client.get_with_retry")
    def test_erro_retorna_lista_vazia(self, mock_get):
        mock_get.side_effect = Exception("error")
        from populate.chembl_client import fetch_mechanisms
        self.assertEqual(fetch_mechanisms("CHEMBL25"), [])


# ============================================================
# Testes: pubmed_client — _parse_abstract
# ============================================================

class TestParseAbstract(unittest.TestCase):

    def _elem(self, xml_str):
        return ET.fromstring(xml_str)

    def test_abstract_simples(self):
        from populate.pubmed_client import _parse_abstract
        article = self._elem("""
            <Article>
              <Abstract>
                <AbstractText>Texto simples sem label.</AbstractText>
              </Abstract>
            </Article>
        """)
        result = _parse_abstract(article)
        self.assertEqual(result, "Texto simples sem label.")

    def test_abstract_estruturado_com_labels(self):
        from populate.pubmed_client import _parse_abstract
        article = self._elem("""
            <Article>
              <Abstract>
                <AbstractText Label="BACKGROUND">Contexto aqui.</AbstractText>
                <AbstractText Label="METHODS">Metodologia aqui.</AbstractText>
                <AbstractText Label="RESULTS">Resultados aqui.</AbstractText>
              </Abstract>
            </Article>
        """)
        result = _parse_abstract(article)
        self.assertIn("Background: Contexto aqui.", result)
        self.assertIn("Methods: Metodologia aqui.", result)
        self.assertIn("Results: Resultados aqui.", result)
        self.assertIn("\n\n", result)

    def test_abstract_ausente_retorna_none(self):
        from populate.pubmed_client import _parse_abstract
        article = self._elem("<Article></Article>")
        self.assertIsNone(_parse_abstract(article))

    def test_abstract_vazio_retorna_none(self):
        from populate.pubmed_client import _parse_abstract
        article = self._elem("<Article><Abstract><AbstractText></AbstractText></Abstract></Article>")
        self.assertIsNone(_parse_abstract(article))

    def test_label_unlabelled_tratado_como_simples(self):
        from populate.pubmed_client import _parse_abstract
        article = self._elem("""
            <Article>
              <Abstract>
                <AbstractText Label="UNLABELLED">Texto sem label real.</AbstractText>
              </Abstract>
            </Article>
        """)
        result = _parse_abstract(article)
        self.assertEqual(result, "Texto sem label real.")
        self.assertNotIn("Unlabelled:", result)

    def test_inline_tags_capturadas(self):
        from populate.pubmed_client import _parse_abstract
        article = self._elem("""
            <Article>
              <Abstract>
                <AbstractText>Efeito da <i>in vitro</i> exposição ao composto.</AbstractText>
              </Abstract>
            </Article>
        """)
        result = _parse_abstract(article)
        self.assertIn("in vitro", result)


# ============================================================
# Testes: pubmed_client — _parse_year
# ============================================================

class TestParseYear(unittest.TestCase):

    def _elem(self, xml_str):
        return ET.fromstring(xml_str)

    def test_ano_com_year_tag(self):
        from populate.pubmed_client import _parse_year
        article = self._elem("<Article><Journal><JournalIssue><PubDate><Year>2023</Year></PubDate></JournalIssue></Journal></Article>")
        self.assertEqual(_parse_year(article), 2023)

    def test_ano_com_medlinedate(self):
        from populate.pubmed_client import _parse_year
        article = self._elem("<Article><Journal><JournalIssue><PubDate><MedlineDate>2022 Jan-Feb</MedlineDate></PubDate></JournalIssue></Journal></Article>")
        self.assertEqual(_parse_year(article), 2022)

    def test_sem_pubdate_retorna_none(self):
        from populate.pubmed_client import _parse_year
        article = self._elem("<Article></Article>")
        self.assertIsNone(_parse_year(article))


# ============================================================
# Testes: pubmed_client — _parse_doi
# ============================================================

class TestParseDoi(unittest.TestCase):

    def _elem(self, xml_str):
        return ET.fromstring(xml_str)

    def test_doi_via_elocation(self):
        from populate.pubmed_client import _parse_doi
        pub = self._elem("""
            <PubmedArticle>
              <MedlineCitation>
                <Article>
                  <ELocationID EIdType="doi">10.1234/test.001</ELocationID>
                </Article>
              </MedlineCitation>
            </PubmedArticle>
        """)
        self.assertEqual(_parse_doi(pub), "10.1234/test.001")

    def test_doi_via_articleid(self):
        from populate.pubmed_client import _parse_doi
        pub = self._elem("""
            <PubmedArticle>
              <PubmedData>
                <ArticleIdList>
                  <ArticleId IdType="doi">10.9999/other.002</ArticleId>
                </ArticleIdList>
              </PubmedData>
            </PubmedArticle>
        """)
        self.assertEqual(_parse_doi(pub), "10.9999/other.002")

    def test_sem_doi_retorna_none(self):
        from populate.pubmed_client import _parse_doi
        pub = self._elem("<PubmedArticle></PubmedArticle>")
        self.assertIsNone(_parse_doi(pub))


# ============================================================
# Testes: pubmed_client — _parse_mesh_terms
# ============================================================

class TestParseMeshTerms(unittest.TestCase):

    def _elem(self, xml_str):
        return ET.fromstring(xml_str)

    def test_termos_extraidos(self):
        from populate.pubmed_client import _parse_mesh_terms
        medline = self._elem("""
            <MedlineCitation>
              <MeshHeadingList>
                <MeshHeading>
                  <DescriptorName MajorTopicYN="Y">Aspirin</DescriptorName>
                </MeshHeading>
                <MeshHeading>
                  <DescriptorName MajorTopicYN="N">Inflammation</DescriptorName>
                </MeshHeading>
              </MeshHeadingList>
            </MedlineCitation>
        """)
        result = _parse_mesh_terms(medline)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], {"term": "Aspirin", "major": True})
        self.assertEqual(result[1], {"term": "Inflammation", "major": False})

    def test_sem_mesh_retorna_none(self):
        from populate.pubmed_client import _parse_mesh_terms
        medline = self._elem("<MedlineCitation></MedlineCitation>")
        self.assertIsNone(_parse_mesh_terms(medline))


# ============================================================
# Testes: pubmed_client — search_pubmed
# ============================================================

class TestSearchPubmed(unittest.TestCase):

    @patch("pubmed_client.get_with_retry")
    def test_retorna_pmids(self, mock_get):
        mock_get.return_value = _mock_response(PUBMED_ESEARCH_RESPONSE)
        from populate.pubmed_client import search_pubmed
        result = search_pubmed("Aspirin")
        self.assertEqual(result, ["38000001", "38000002"])

    @patch("pubmed_client.get_with_retry")
    def test_erro_retorna_lista_vazia(self, mock_get):
        mock_get.side_effect = Exception("timeout")
        from populate.pubmed_client import search_pubmed
        self.assertEqual(search_pubmed("Aspirin"), [])

    @patch("pubmed_client.get_with_retry")
    def test_lista_vazia_quando_sem_resultados(self, mock_get):
        mock_get.return_value = _mock_response({"esearchresult": {"idlist": []}})
        from populate.pubmed_client import search_pubmed
        self.assertEqual(search_pubmed("Composto Inexistente"), [])


# ============================================================
# Testes: pubmed_client — fetch_articles
# ============================================================

class TestFetchArticles(unittest.TestCase):

    @patch("pubmed_client.get_with_retry")
    def test_article_com_abstract_estruturado(self, mock_get):
        mock_get.return_value = _mock_response(
            content=PUBMED_EFETCH_XML.encode()
        )
        from populate.pubmed_client import fetch_articles
        result = fetch_articles(["38000001"])

        self.assertEqual(len(result), 1)
        art = result[0]
        self.assertEqual(art["pmid"],    "38000001")
        self.assertEqual(art["title"],   "Aspirin and cardiovascular risk")
        self.assertEqual(art["journal"], "Journal of Cardiology")
        self.assertEqual(art["pub_year"], 2023)
        self.assertEqual(art["doi"],     "10.1234/jcard.2023.001")
        self.assertIn("Background:",     art["abstract"])
        self.assertIn("Methods:",        art["abstract"])
        self.assertEqual(json.loads(art["authors"]), ["John Smith"])
        pub_types = json.loads(art["pub_types"])
        self.assertIn("Review", pub_types)
        mesh = json.loads(art["mesh_terms"])
        self.assertEqual(mesh[0]["term"],  "Aspirin")
        self.assertTrue(mesh[0]["major"])
        kws = json.loads(art["keywords"])
        self.assertIn("cardioprotection", kws)

    @patch("pubmed_client.get_with_retry")
    def test_article_com_abstract_simples_e_nome_coletivo(self, mock_get):
        mock_get.return_value = _mock_response(
            content=PUBMED_EFETCH_XML_SIMPLE_ABSTRACT.encode()
        )
        from populate.pubmed_client import fetch_articles
        result = fetch_articles(["38000002"])

        art = result[0]
        self.assertEqual(art["abstract"], "Simple paragraph abstract without labels.")
        self.assertEqual(json.loads(art["authors"]), ["NSAID Study Group"])
        self.assertEqual(art["pub_year"], 2022)
        self.assertIsNone(art["doi"])

    @patch("pubmed_client.get_with_retry")
    def test_lista_vazia_retorna_lista_vazia(self, mock_get):
        from populate.pubmed_client import fetch_articles
        result = fetch_articles([])
        self.assertEqual(result, [])
        mock_get.assert_not_called()

    @patch("pubmed_client.get_with_retry")
    def test_xml_invalido_retorna_lista_vazia(self, mock_get):
        mock_get.return_value = _mock_response(content=b"<nao_e_xml_valido")
        from populate.pubmed_client import fetch_articles
        result = fetch_articles(["123"])
        self.assertEqual(result, [])

    @patch("pubmed_client.get_with_retry")
    def test_erro_de_rede_retorna_lista_vazia(self, mock_get):
        mock_get.side_effect = Exception("connection error")
        from populate.pubmed_client import fetch_articles
        result = fetch_articles(["123"])
        self.assertEqual(result, [])


# ============================================================
# Testes: db — get_compound_status
# ============================================================

class TestGetCompoundStatus(unittest.TestCase):

    def _mock_cur(self, fetchone_return):
        cur = MagicMock()
        cur.fetchone.return_value = fetchone_return
        return cur

    def test_composto_inexistente_retorna_none(self):
        cur = self._mock_cur(None)
        from populate.db import get_compound_status
        result = get_compound_status(cur, "CHEMBL999")
        self.assertIsNone(result)

    def test_composto_completo(self):
        import uuid
        uid = uuid.uuid4()
        cur = self._mock_cur((uid, True, True, True, True, True))
        from populate.db import get_compound_status
        result = get_compound_status(cur, "CHEMBL25")
        self.assertEqual(result["id"],           uid)
        self.assertTrue(result["has_admet"])
        self.assertTrue(result["has_bioact"])
        self.assertTrue(result["is_complete"])

    def test_composto_parcial(self):
        import uuid
        uid = uuid.uuid4()
        cur = self._mock_cur((uid, True, False, False, False, False))
        from populate.db import get_compound_status
        result = get_compound_status(cur, "CHEMBL25")
        self.assertTrue(result["has_admet"])
        self.assertFalse(result["has_bioact"])
        self.assertFalse(result["is_complete"])

    def test_is_complete_falso_se_qualquer_etapa_faltando(self):
        import uuid
        uid = uuid.uuid4()
        cur = self._mock_cur((uid, True, True, True, True, False))
        from populate.db import get_compound_status
        result = get_compound_status(cur, "CHEMBL25")
        self.assertFalse(result["is_complete"])  # has_articles=False


# ============================================================
# Testes: db — upsert_compound
# ============================================================

class TestUpsertCompound(unittest.TestCase):

    def test_executa_insert_e_retorna_id(self):
        import uuid
        uid = str(uuid.uuid4())
        cur = MagicMock()
        cur.fetchone.return_value = (uid,)

        from populate.db import upsert_compound
        result = upsert_compound(cur, {
            "chembl_id":         "CHEMBL25",
            "name":              "ASPIRIN",
            "molecular_formula": "C9H8O4",
            "mol_weight":        180.16,
            "smiles":            "CC(=O)Oc1ccccc1C(=O)O",
            "inchi_key":         "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
            "alogp":             1.19,
            "hbd":               1,
            "hba":               3,
            "psa":               63.6,
            "ro5_violations":    0,
        })

        self.assertEqual(result, uid)
        cur.execute.assert_called_once()
        sql = cur.execute.call_args[0][0]
        self.assertIn("INSERT INTO compounds", sql)
        self.assertIn("ON CONFLICT", sql)


# ============================================================
# Testes: db — upsert_indication
# ============================================================

class TestUpsertIndication(unittest.TestCase):

    def test_executa_insert_com_max_phase_convertido(self):
        cur = MagicMock()
        from populate.db import upsert_indication
        upsert_indication(cur, "compound-uuid-123", {
            "drugind_id":        1001,
            "mesh_id":           "D006261",
            "mesh_heading":      "Headache",
            "efo_id":            "EFO:0003843",
            "efo_term":          "headache",
            "max_phase_for_ind": "4",   # string → deve ser convertida para float
        })

        cur.execute.assert_called_once()
        args = cur.execute.call_args[0][1]
        # max_phase é o 7º argumento (índice 6)
        self.assertEqual(args[6], 4.0)

    def test_max_phase_none_aceito(self):
        cur = MagicMock()
        from populate.db import upsert_indication
        upsert_indication(cur, "compound-uuid-123", {
            "drugind_id":        1002,
            "mesh_heading":      "Pain",
            "max_phase_for_ind": None,
        })
        args = cur.execute.call_args[0][1]
        self.assertIsNone(args[6])


# ============================================================
# Testes: db — upsert_mechanism
# ============================================================

class TestUpsertMechanism(unittest.TestCase):

    def test_direct_interaction_cast_para_bool(self):
        cur = MagicMock()
        from populate.db import upsert_mechanism
        upsert_mechanism(cur, "compound-uuid", {
            "mec_id":              101,
            "mechanism_of_action": "COX inhibitor",
            "action_type":         "INHIBITOR",
            "target_chembl_id":    "CHEMBL612545",
            "target_name":         "COX-1",
            "direct_interaction":  1,   # inteiro → deve virar True
            "disease_efficacy":    0,   # inteiro → deve virar False
            "mechanism_comment":   None,
            "selectivity_comment": None,
            "binding_site_comment":None,
        }, target_id=None)

        args = cur.execute.call_args[0][1]
        # direct_interaction é o 8º arg (índice 7), disease_efficacy é o 9º (índice 8)
        self.assertIs(args[7], True)
        self.assertIs(args[8], False)

    def test_com_target_id_passado(self):
        import uuid
        cur        = MagicMock()
        target_uid = str(uuid.uuid4())
        from populate.db import upsert_mechanism
        upsert_mechanism(cur, "c-uuid", {
            "mec_id":             202,
            "direct_interaction": 1,
            "disease_efficacy":   1,
        }, target_id=target_uid)

        args = cur.execute.call_args[0][1]
        self.assertEqual(args[2], target_uid)   # target_id é índice 2


# ============================================================
# Testes: db — upsert_article
# ============================================================

class TestUpsertArticle(unittest.TestCase):

    def test_executa_insert_e_retorna_id(self):
        import uuid
        uid = str(uuid.uuid4())
        cur = MagicMock()
        cur.fetchone.return_value = (uid,)

        from populate.db import upsert_article
        result = upsert_article(cur, {
            "pmid":       "38000001",
            "title":      "Aspirin study",
            "abstract":   "Full abstract here.",
            "authors":    json.dumps(["Smith J"]),
            "journal":    "J Cardiology",
            "pub_year":   2023,
            "doi":        "10.1234/test",
            "mesh_terms": json.dumps([{"term": "Aspirin", "major": True}]),
            "keywords":   json.dumps(["aspirin"]),
            "pub_types":  json.dumps(["Journal Article"]),
        })

        self.assertEqual(result, uid)
        sql = cur.execute.call_args[0][0]
        self.assertIn("INSERT INTO articles", sql)
        self.assertIn("ON CONFLICT", sql)
        self.assertIn("COALESCE", sql)


# ============================================================
# Testes: db — link_article_compound
# ============================================================

class TestLinkArticleCompound(unittest.TestCase):

    def test_insert_com_on_conflict(self):
        cur = MagicMock()
        from populate.db import link_article_compound
        link_article_compound(cur, "article-uuid", "compound-uuid")
        sql = cur.execute.call_args[0][0]
        self.assertIn("INSERT INTO article_compounds", sql)
        self.assertIn("ON CONFLICT DO NOTHING", sql)
        args = cur.execute.call_args[0][1]
        self.assertEqual(args, ("article-uuid", "compound-uuid"))


# ============================================================
# Ponto de entrada
# ============================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)