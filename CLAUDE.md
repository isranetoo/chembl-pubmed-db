# DrugXPert — Instruções para o Claude

> Banco farmacológico que combina **ChEMBL** (compostos, ADMET, bioatividades, mecanismos, indicações, alvos), **PubMed** (artigos), **ClinicalTrials.gov** (ensaios clínicos), **Owkin** (histopatologia/TCGA) e classificação **ATC/WHO**, exposto via API FastAPI, dashboard Streamlit e frontend React/Vite. Postgres é o storage central — roda local via Docker **ou** direto no Supabase.

Ambiente principal de desenvolvimento: **Windows + PowerShell**. Caminho do repo: `C:\Users\Israel Neto\Desktop\DrugXpert\chembl-pubmed-db`.

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Linguagens | Python 3.11+, Node 18+ |
| Backend | FastAPI + uvicorn |
| Dashboard | Streamlit |
| Frontend | React + Vite (TanStack Query) |
| Banco | Postgres 15/16 (Docker local ou Supabase) |
| Migrations | **Alembic** + SQL bruto em `database/init/` |
| Scheduling | APScheduler (sexta 06:00 BRT) |
| Testes | pytest com mocks |

---

## Setup rápido (do zero)

```powershell
# 1. ambiente virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. banco local
docker compose up -d

# 3. registrar baseline + aplicar migrations
alembic stamp 0001_baseline
alembic upgrade head

# 4. popular
python populate.py

# 5. validar e refrescar views
python scripts/validate_db.py
python scripts/refresh.py

# 6. subir API (terminal 1)
uvicorn api:app --reload --port 8000

# 7. dashboard (terminal 2 — reativar .venv)
streamlit run dashboard.py

# 8. frontend (terminal 3)
cd frontend
npm install
npm run dev
```

---

## Comandos por categoria

### Populate (pipeline incremental)
```powershell
python populate.py                                   # incremental, default
python populate.py --add CHEMBL941                   # adicionar composto extra
python populate.py --only CHEMBL25 --only CHEMBL941  # rodar SÓ esses
python populate.py --only-compounds                  # pular bioact/ind/mec/pubmed/trials/targets
python populate.py --skip-pubmed                     # pular PubMed (internet lenta)
python populate.py --skip-trials                     # pular CT.gov
python populate.py --force                           # ignorar cache, reprocessar tudo
```

### Scraper (descobrir novos compostos ChEMBL)
```powershell
python -m populate.scraper --start 10000 --end 15000
python -m populate.scraper --start 10000 --end 15000 --category "Oncologia"
python -m populate.scraper --start 10000 --end 15000 --export-csv compostos.csv
```
Sempre seguido de `python populate.py` pra popular os IDs novos.

### Scripts em `scripts/` (cirúrgicos, idempotentes)
```powershell
python scripts/validate_db.py                                  # integridade
python scripts/validate_db.py --section compounds              # seção específica
python scripts/refresh.py                                      # refrescar materialized views
python scripts/refresh.py --status                             # status das views
python scripts/backfill_compound_metadata.py [--dry-run]       # migration 0004
python scripts/backfill_bioactivity_enrich.py [--limit N]      # migration 0005
python scripts/backfill_target_enrich.py [--limit N]           # migration 0006
python scripts/backfill_abstracts.py                           # abstracts PubMed faltantes
python scripts/populate_clinical_trials.py [--limit N] [--skip-synced] [--start-from CHEMBL2000]
```
Todos aceitam `--only`, `--limit`, `--dry-run`. Use quando puxar código novo num banco já populado e quiser **só** uma camada — sem rodar `populate.py` inteiro.

### Migrations (Alembic)
```powershell
alembic upgrade head           # aplicar pendentes
alembic stamp 0001_baseline    # marcar baseline sem executar SQL (volume já populado pelos init/*.sql)
alembic current                # ver versão atual
alembic history                # listar migrations
```

### Docker
```powershell
docker compose up -d                       # subir Postgres + pgAdmin
docker compose ps                          # status
docker compose logs -f <serviço>           # logs
docker compose down                        # parar (mantém volume)
docker compose down -v                     # APAGA o volume (banco do zero)
```

### Testes
```powershell
pytest tests/ -v
pytest tests/test_modules.py -v
```

---

## Portas e serviços

| Serviço | URL | Container |
|---------|-----|-----------|
| API FastAPI | http://localhost:8000/docs | — |
| Health check | http://localhost:8000/health | — |
| Dashboard Streamlit | http://localhost:8501 | — |
| Frontend Vite dev | http://localhost:5173 | — |
| Postgres | localhost:5432 | `chembl_pubmed_db` |
| pgAdmin | http://localhost:5050 | — |

Credenciais default do banco local: `admin / admin123 / chembl_pubmed`. pgAdmin: `israneto20@gmail.com / admin123`.

---

## Arquitetura do repo

```
chembl-pubmed-db/
├── populate/                  # pacote do pipeline de ingestão
│   ├── __init__.py
│   ├── chembl_client.py       # API ChEMBL (EBI)
│   ├── pubmed_client.py       # E-utilities (NCBI)
│   ├── ctgov_client.py        # ClinicalTrials.gov v2 (retry 3x: 5s/10s/20s)
│   ├── owkin_client.py        # Owkin (histopatologia)
│   ├── db.py                  # persistência (upsert idempotente)
│   ├── config.py              # DB_CONFIG, constantes
│   ├── http_retry.py          # wrapper requests com backoff
│   ├── scheduler.py           # APScheduler
│   └── scraper.py             # descoberta de IDs ChEMBL → seed_compounds
├── database/init/             # SQL bruto — só roda em volume VAZIO
│   ├── 01_schema.sql
│   ├── 02_article_enrich.sql
│   ├── 03_indications.sql
│   ├── 04_mechanisms.sql
│   ├── 05_admet.sql
│   ├── 06_fts.sql
│   ├── 07_materialized_views.sql
│   └── 08_owkin_histopathology.sql
├── alembic/versions/          # migrations versionadas
│   ├── 0001_baseline.py
│   ├── 0002_seed_compounds.py
│   ├── 0003_clinical_trials.py
│   ├── 0004_compound_metadata.py
│   ├── 0005_bioactivity_enrich.py
│   ├── 0006_target_enrich.py
│   └── 0007_mechanism_variants.py
├── scripts/                   # CLI utils (validate, refresh, backfills)
├── frontend/                  # React + Vite (NÃO é frontend/frontend/)
│   └── src/
├── tests/                     # pytest com mocks
├── populate.py                # entry point do pipeline (raiz, não dentro de populate/)
├── api.py                     # FastAPI app
├── dashboard.py               # Streamlit
├── migrate_to_supabase.py     # copia local → Supabase (respeita ordem FK)
├── docker-compose.yml
└── requirements.txt
```

---

## Pipeline `populate.py` — 8 etapas por composto

Cada etapa tem uma **sentinela** que evita re-trabalho. Compostos completos imprimem `Ja completo — pulando`, parciais imprimem `[PARCIAL] Faltando: <etapas>`.

| # | Etapa | Sentinela de "já feito" |
|---|-------|------------------------|
| 1 | Metadata clínico (compound + synonyms + ATC) | `compounds.molecule_type IS NOT NULL` |
| 2 | ADMET | linha em `admet_properties` |
| 3 | Bioatividades enriquecidas | `bioactivities.assay_type` não-NULL (linhas legadas são apagadas e refetched) |
| 4 | Indicações terapêuticas (MeSH + EFO + max_phase) | — |
| 5 | Mecanismos (com `variant_sequence` quando há mutação) | — |
| 6 | Artigos PubMed (abstract, MeSH, keywords, pub_types) | — |
| 7 | Ensaios clínicos (CT.gov) | link em `compound_clinical_trials` |
| 8 | Enrichment de alvos (UniProt/gene/PDB/GO/Reactome) | `targets.tax_id IS NOT NULL` |

Para a primeira execução em ~50 compostos, contar minutos. Re-execuções subsequentes são quase instantâneas.

---

## Banco — dois fluxos suportados

### Fluxo 1 — Local primeiro, Supabase depois (default)
Sem `DATABASE_URL`, o projeto conecta no Docker local. Pra subir o banco populado:
```powershell
$env:DATABASE_URL = "postgresql://postgres.xxx:senha@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"
python migrate_to_supabase.py
python migrate_to_supabase.py --only compound_synonyms --only compound_atc   # parcial
```

### Fluxo 2 — Direto no Supabase
```powershell
$env:DATABASE_URL = "postgresql://..."
alembic upgrade head           # cria tabelas no Supabase
python populate.py             # popula direto
uvicorn api:app --reload --port 8000
```
Nesse fluxo: pula Docker, pula `migrate_to_supabase.py`.

Ordem de resolução do banco em `populate/config.py`:
1. `DATABASE_URL` (se setada)
2. `DB_HOST`/`DB_PORT`/`DB_NAME`/`DB_USER`/`DB_PASSWORD` individuais
3. Defaults do Docker local (`postgres / 5432 / chembl_pubmed / admin / admin123`)

---

## Convenções

### Python
- **DB writes** sempre via funções de `populate/db.py` — são **upserts idempotentes**. Não usar `INSERT` cru no pipeline.
- **HTTP externo** sempre via `populate/http_retry.py` — backoff exponencial pra ChEMBL/PubMed; cliente CT.gov tem retry 3x (5s/10s/20s).
- **Scripts em `scripts/`** precisam adicionar a raiz ao `sys.path` antes dos imports do projeto:
  ```python
  import sys
  from pathlib import Path
  sys.path.insert(0, str(Path(__file__).parent.parent))
  ```
  Todos os scripts existentes já têm — replicar em scripts novos.
- **Logs**: gravar em `populate/logs/` com timestamp. Não usar `print()` no pipeline (use logging).
- **Testes**: mocks pra ChEMBL/PubMed/CT.gov/Owkin — zero I/O real. `conftest.py` mocka o pool psycopg2.

### SQL / Migrations
- **Nunca editar migration Alembic já aplicada** — sempre criar nova.
- Arquivos em `database/init/*.sql` só rodam automaticamente quando o **volume do Postgres está vazio**. Em banco existente, usar `alembic upgrade head`.
- Toda migration deve ser **idempotente**: `ADD COLUMN IF NOT EXISTS`, `CREATE TABLE IF NOT EXISTS`, `DO $$ ... EXCEPTION WHEN duplicate_object` para enums.
- Convenção de nome Alembic: `NNNN_descricao.py` (zero-padded, 4 dígitos).
- Para Supabase, habilitar RLS com `select using (true)` pra dado público. Service role escreve, anônimo lê.

### Frontend
- **Stack fixa**: React + Vite + TanStack Query. Não migrar pra Next/CRA.
- **Estilo glassmorphism**: gradient bg, backdrop-blur, border sutil, hover lift. Manter consistência com `StatCard`, `Pill`, `Shell`.
- **API client**: tudo via `src/lib/api.js`. Hooks via TanStack Query em `src/lib/hooks.js`.
- **URL da API**: `VITE_API_BASE_URL` em `.env` — nunca hardcoded.
- **Abas do perfil do composto**: Overview, ADMET, Indicações, Mecanismos, Bioatividades, Clinical Status, Artigos. Header tem badges automáticas (fase, ano aprovação, vias, warnings, USAN stem, ATC).

### API REST — endpoints da camada Clinical Trials
```
POST /compounds/{chembl_id}/trials/sync           # sincroniza com CT.gov
POST /compounds/{chembl_id}/trials/sync?drug_name=imatinib   # força nome de busca
GET  /compounds/{chembl_id}/trials                # cache (sem hit CT.gov)
GET  /compounds/{chembl_id}/trials?phase=PHASE3&status=RECRUITING
```

---

## Quirks reais do projeto

- **`frontend/` é flat**, não `frontend/frontend/`.
- **`populate.py` fica na raiz** (não dentro do pacote `populate/`). Rodar com `python populate.py`, não `python -m populate.populate`.
- **Compostos com nome IUPAC** (ex: `1,2,3,4-TETRAHYDROISOQUINOLINE`) tipicamente retornam 0 trials na CT.gov — não é erro, é "Sem trials" no resumo. Pra esses casos, usar `--drug-name` no `populate_clinical_trials.py` pra forçar o nome correto.
- **Falhas de CT.gov no populate.py não derrubam o composto** — vão pra warning e o pipeline segue.
- **Imatinib (CHEMBL941)** tem ~700 trials, sync leva ~20s. Compostos populares (aspirin, etc.) podem ter centenas.
- **Bulk populate da CT.gov** (`scripts/populate_clinical_trials.py`) roda cada composto em **transação isolada** — erro em um não derruba o batch.
- **Scraper usa `ON CONFLICT DO NOTHING`** — rodar 2x na mesma faixa é seguro, não duplica nem sobrescreve categorias editadas manualmente.
- **Após `git pull` com migrations novas em banco já populado**: rodar `alembic upgrade head`. SQLs em `database/init/` **não rodam** porque o volume não está vazio.

---

## MCPs disponíveis (preferir sobre HTTP direto)

Quando precisar consultar dados externos:
- **ChEMBL MCP** — compostos, alvos, bioatividades, drogas aprovadas, ADMET, mecanismos
- **PubMed MCP** — busca de artigos, metadata, full-text
- **Clinical Trials MCP** — ensaios por composto/sponsor/elegibilidade
- **Owkin MCP** — histopatologia, coortes TCGA, survival analysis
- **Supabase MCP** — gerenciar banco em produção (migrations, queries, RLS, edge functions)

Os MCPs já cuidam de paginação, rate limit e parsing — usar em vez de `requests` direto pra exploração/debug.

---

## Antes de modificar coisas importantes

1. **Schema do banco**: criar migration Alembic nova + SQL em `database/init/` se for relevante pra fresh install. Nunca editar migration aplicada. Rodar `python scripts/validate_db.py` depois.
2. **`populate/config.py`**: a lista de compostos sai de `seed_compounds` (populada pelo scraper ou migration `0002`). Não hardcodar IDs.
3. **Endpoints da API**: documentar no Swagger (docstring + Pydantic schema). Manter compatibilidade com `frontend/src/lib/api.js`.
4. **Materialized views**: se alterar tabela base, rodar `python scripts/refresh.py`. Caso contrário queries servem dados stale.
5. **Migrations 0004–0007** adicionam colunas em compostos antigos vazias — sempre rodar o backfill correspondente em `scripts/` (ou `populate.py` que cobre tudo automaticamente).