"""
conftest.py
-----------
Configuração global do pytest.

Resolve dois problemas antes de qualquer teste rodar:

1. PATH — adiciona o diretório raiz do projeto ao sys.path para que
   chembl_client, pubmed_client, db, config e http_retry sejam
   encontrados independentemente de onde o pytest é chamado.

2. MOCKS de dependências externas — psycopg2 e requests podem não
   estar instalados no ambiente de CI/test. Este arquivo os substitui
   por MagicMocks antes de qualquer import, evitando ImportError.
   Os testes individuais usam @patch para controlar o comportamento.
"""

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

# ── 1. Adicionar raiz do projeto ao sys.path ─────────────────────────────────
ROOT = Path(__file__).parent.parent.resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ── 2. Mock de psycopg2 (banco de dados) ─────────────────────────────────────
# db.py importa psycopg2 no topo do módulo. Se não estiver instalado,
# o import falha antes mesmo de qualquer teste rodar.
if "psycopg2" not in sys.modules:
    psycopg2_mock = types.ModuleType("psycopg2")
    psycopg2_mock.connect   = MagicMock()
    psycopg2_mock.extras    = types.ModuleType("psycopg2.extras")
    psycopg2_mock.errors    = types.ModuleType("psycopg2.errors")

    # UndefinedTable é usado em validate_db.py
    psycopg2_mock.errors.UndefinedTable = type(
        "UndefinedTable", (Exception,), {}
    )

    sys.modules["psycopg2"]        = psycopg2_mock
    sys.modules["psycopg2.extras"] = psycopg2_mock.extras
    sys.modules["psycopg2.errors"] = psycopg2_mock.errors


# ── 3. Mock de requests ───────────────────────────────────────────────────────
# chembl_client e pubmed_client importam requests.
# Os testes usam @patch("chembl_client.get_with_retry") para controlar
# as respostas — mas o import do módulo ainda precisa de requests.
if "requests" not in sys.modules:
    requests_mock = types.ModuleType("requests")
    requests_mock.get        = MagicMock()
    requests_mock.Response   = MagicMock()
    requests_mock.exceptions = types.SimpleNamespace(
        ConnectionError = ConnectionError,
        Timeout         = TimeoutError,
        HTTPError       = Exception,
    )
    sys.modules["requests"] = requests_mock