# Guia Rápido — Como Rodar o Projeto

Siga os passos abaixo na ordem. Cada bloco explica o que o comando faz.

---

## Pré-requisitos

Antes de começar, instale:

- [Python 3.11+](https://www.python.org/downloads/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Node.js 18+](https://nodejs.org/) (só se quiser rodar o frontend)

---

## Passo 1 — Entrar na pasta do projeto

```powershell
cd C:\Users\Israel Neto\Desktop\DrugXpert\chembl-pubmed-db
```

> Define o diretório de trabalho para todos os comandos seguintes.

---

## Passo 2 — Criar o ambiente virtual Python

```powershell
python -m venv .venv
```

> Cria uma pasta `.venv` isolada com a versão do Python instalada, evitando conflitos com outros projetos.

---

## Passo 3 — Ativar o ambiente virtual

```powershell
.\.venv\Scripts\Activate.ps1
```

> Ativa o ambiente. O terminal vai mostrar `(.venv)` no início da linha quando estiver ativo.

---

## Passo 4 — Instalar as dependências Python

```powershell
pip install -r requirements.txt
```

> Instala todas as bibliotecas do projeto: FastAPI, Streamlit, psycopg2, Alembic, APScheduler, etc.

---

## Passo 5 — Subir o banco de dados (PostgreSQL + pgAdmin)

```powershell
docker compose up -d
```

> Inicia dois containers em segundo plano:
> - **PostgreSQL** em `localhost:5432` — o banco de dados principal
> - **pgAdmin** em `http://localhost:5050` — interface web para gerenciar o banco
>
> Login pgAdmin: `israneto20@gmail.com` / senha: `admin123`
>
> O Docker já cria todas as tabelas automaticamente na primeira vez que o volume é criado.

---

## Passo 6 — Registrar o baseline e aplicar migrations

```powershell
alembic stamp 0001_baseline
alembic upgrade head
```

> - `stamp 0001_baseline`: marca o schema inicial como já aplicado **sem executar SQL** (o Docker já criou as tabelas via `01_schema.sql` a `08_owkin_histopathology.sql`).
> - `upgrade head`: aplica as migrations restantes:
>   - `0002_seed_compounds` — popula `seed_compounds` com 51 compostos padrão
>   - `0003_clinical_trials` — tabelas de ensaios clínicos (CT.gov)
>   - `0004_compound_metadata` — campos clínicos/regulatórios + synonyms + ATC
>   - `0005_bioactivity_enrich` — pchembl, assay metadata, ligand efficiency, variantes
>   - `0006_target_enrich` — UniProt/gene symbol, PDB, GO, Reactome
>   - `0007_mechanism_variants` — `variant_sequence` JSONB em mechanisms
>
> Pular esse passo faz o `populate.py` falhar com erro de "tabela seed_compounds não existe" ou colunas faltantes.

### O que cada migration nova adiciona

| Migration | Tabelas/Colunas | Para que serve |
|-----------|-----------------|----------------|
| `0004_compound_metadata` | Em `compounds`: `max_phase`, `first_approval`, `molecule_type`, `oral/parenteral/topical`, `black_box_warning`, `withdrawn_*`, `prodrug`, `orphan`, `usan_stem(_definition)`, `inchi`. Tabelas `compound_synonyms` (INN/BAN/trade names) e `compound_atc` (classificação ATC da WHO). | Status clínico/regulatório do composto. Badges no header do front: fase, ano de aprovação, vias, warnings, drug class. |
| `0005_bioactivity_enrich` | Em `bioactivities`: `activity_id` (PK do ChEMBL), `pchembl_value`, `assay_chembl_id/type/description`, `target_organism/tax_id`, `document_journal/year`, `bei/le/lle/sei`, `assay_variant_mutation`. UNIQUE parcial em `activity_id`. | pChEMBL padronizado pra ranking de potência, fonte literária, mutações estudadas, ligand efficiency. |
| `0006_target_enrich` | Em `targets`: `tax_id`, `species_group_flag`. Tabelas `target_components` (UniProt accession, gene symbol, tipo) e `target_xrefs` (PDB, GO, Reactome, InterPro, Pfam). | Gene symbol + link UniProt nas bioativatividades/mecanismos, base pra viewer 3D e GO. |
| `0007_mechanism_variants` | `mechanisms.variant_sequence` JSONB. | Mutações associadas a mecanismos (ex: T315I em BCR-ABL — essencial pra estudar resistência). |

---

## Passo 7 — Popular o banco com dados do ChEMBL, PubMed e CT.gov

```powershell
python populate.py
```

> Pipeline incremental e idempotente. Roda 8 etapas por composto e pula automaticamente o que já está no banco:
>
> 1. **Metadata clínico** (compound + synonyms + ATC) — sentinela: `compounds.molecule_type IS NOT NULL`
> 2. **ADMET** — sentinela: linha em `admet_properties`
> 3. **Bioatividades enriquecidas** — sentinela: bioatividades com `assay_type` não-NULL. Linhas legadas (sem assay_type) são apagadas e re-fetched.
> 4. **Indicações terapêuticas** (MeSH + EFO + max_phase)
> 5. **Mecanismos** (com `variant_sequence` quando houver mutação)
> 6. **Artigos do PubMed** (abstract, MeSH, keywords, pub_types)
> 7. **Ensaios clínicos (CT.gov)** — sentinela: link em `compound_clinical_trials`
> 8. **Enrichment de alvos** — para cada target usado pelo composto sem `tax_id`, faz fetch completo: components (UniProt/gene) + xrefs (PDB/GO/Reactome)
>
> Compostos completamente populados imprimem `Ja completo — pulando`. Compostos parciais imprimem `[PARCIAL] Faltando: <etapas>` e só executam o que falta.
>
> Pode demorar minutos na primeira execução; nas seguintes é praticamente instantâneo.

### Flags úteis

```powershell
# Adicionar um composto extra (preserva a lista padrão)
python populate.py --add CHEMBL941

# Rodar SÓ os compostos especificados
python populate.py --only CHEMBL25 --only CHEMBL941

# Pular etapas pesadas
python populate.py --skip-pubmed
python populate.py --skip-trials

# Só estrutura/ADMET (pula bioact, ind, mec, pubmed, trials, targets_enrich)
python populate.py --only-compounds

# Re-processar do zero ignorando o cache incremental
python populate.py --force
```

---

## Passo 8 — Validar se os dados foram carregados

```powershell
python scripts/validate_db.py
```

> Verifica se o banco está com dados, se as chaves estrangeiras estão íntegras e se as views existem. Exibe um relatório de saúde do banco.

---

## Passo 9 — Atualizar as views materializadas

```powershell
python scripts/refresh.py
```

> Atualiza as views consolidadas que a API e o dashboard usam nas consultas. Necessário após popular ou atualizar dados.

---

## Passo 10 — Subir a API

```powershell
uvicorn api:app --reload --port 8000
```

> Inicia a API FastAPI. Deixe esse terminal aberto enquanto usar o frontend ou o Streamlit.
>
> - API: `http://localhost:8000`
> - Documentação interativa (Swagger): `http://localhost:8000/docs`
> - Health check: `http://localhost:8000/health`

---

## Passo 11 — Subir o dashboard Streamlit

Abra um **novo terminal**, ative o ambiente virtual e rode:

```powershell
.\.venv\Scripts\Activate.ps1
streamlit run dashboard.py
```

> Abre uma interface visual no navegador para explorar compostos, artigos e métricas.
>
> Abre automaticamente em: `http://localhost:8501`

---

## Passo 12 — Subir o frontend React (opcional)

Abra mais um **novo terminal** e rode:

```powershell
cd frontend
npm install
npm run dev
```

> - `npm install`: baixa as dependências do frontend (só precisa rodar uma vez)
> - `npm run dev`: inicia o servidor de desenvolvimento Vite
>
> Abre em: `http://localhost:5173`
>
> O frontend consome a API do Passo 10, então a API precisa estar rodando.
>
> No perfil do composto, abas disponíveis: **Overview, ADMET, Indicações, Mecanismos, Bioatividades, Clinical Status, Artigos**.
>
> O header do composto exibe badges automáticas com fase clínica + ano de aprovação, vias de administração, `Black box warning`, `Withdrawn`, drug class (USAN stem) e o código ATC. A aba **Bioatividades** mostra pChEMBL com cor por potência, gene symbol + link UniProt, jornal/ano e mutação do ensaio. A aba **Mecanismos** mostra gene/UniProt e chip `mut: T315I` quando há `variant_sequence`.

---

## Scripts de backfill (recuperar dados antigos)

Quando você puxa código novo com migrations 0004+, os compostos já existentes no banco ficam com os campos novos vazios. O `populate.py` cobre tudo automaticamente, mas se você quer rodar **só** uma camada — sem o overhead do pipeline completo — use um dos scripts abaixo. Todos aceitam `--only`, `--limit`, `--dry-run` e são idempotentes.

```powershell
# Metadata clínico em compostos antigos (migration 0004)
#   Preenche max_phase, first_approval, oral/parenteral, withdrawn_*,
#   usan_stem, ATC, synonyms.
python scripts/backfill_compound_metadata.py --only CHEMBL941 --dry-run
python scripts/backfill_compound_metadata.py

# Bioatividades enriquecidas em compostos antigos (migration 0005)
#   Apaga linhas sem assay_type e re-fetch com pChEMBL, assay metadata,
#   document_journal, BEI/LE/LLE/SEI, variantes.
python scripts/backfill_bioactivity_enrich.py --limit 5 --dry-run
python scripts/backfill_bioactivity_enrich.py

# Enrichment de alvos antigos (migration 0006)
#   Preenche targets.tax_id + target_components (UniProt/gene) + xrefs
#   (PDB, GO, Reactome). Itera só targets onde tax_id IS NULL.
python scripts/backfill_target_enrich.py --limit 5 --dry-run
python scripts/backfill_target_enrich.py

# Abstracts de artigos antigos do PubMed
python scripts/backfill_abstracts.py
```

> Use os backfills quando puxar código novo num banco já populado **e** não quiser esperar o `populate.py` reler tudo. Para um banco vazio ou em primeira execução, o `populate.py` resolve sozinho.

---

## Atualizando após git pull (banco já populado)

Os arquivos em `database/init/*.sql` só rodam automaticamente quando o volume do Postgres está **vazio**. Se você puxou mudanças que incluem migrations novas e seu banco já está populado, basta rodar:

```powershell
alembic upgrade head
```

> Aplica todas as migrations pendentes (0002 → 0007 nesta versão). Cada uma chama o `.sql` correspondente em `database/init/`. Os SQLs são idempotentes (`ADD COLUMN IF NOT EXISTS`, `CREATE TABLE IF NOT EXISTS`), então re-execução é segura.

Se preferir aplicar um SQL específico direto no banco (sem mexer no Alembic):

```powershell
# Exemplo: aplicar 12_target_enrich.sql num banco existente
Get-Content database\init\12_target_enrich.sql | docker exec -i chembl_pubmed_db psql -U admin -d chembl_pubmed
```

Depois, atualize as dependências Python e reinicie a API:

```powershell
pip install -r requirements.txt
# Ctrl+C no terminal do uvicorn e suba de novo
uvicorn api:app --reload --port 8000
```

> Se o front estava aberto, basta dar refresh — o Vite faz hot-reload e o React Query rebusca.

---

## Camada Clinical Trials — popular um composto

A aba **Clinical Status** carrega vazia até o composto ter sido sincronizado pelo menos uma vez. O `populate.py` já faz isso automaticamente (etapa 7). Pra popular ad-hoc via API:

```powershell
# Sincroniza usando compounds.name como termo de busca na CT.gov
curl -X POST http://localhost:8000/compounds/CHEMBL941/trials/sync

# Ou força um nome específico (útil quando o name no banco é IUPAC)
curl -X POST "http://localhost:8000/compounds/CHEMBL941/trials/sync?drug_name=imatinib"

# Lê o cache (não bate na CT.gov)
curl http://localhost:8000/compounds/CHEMBL941/trials

# Com filtros
curl "http://localhost:8000/compounds/CHEMBL941/trials?phase=PHASE3&status=RECRUITING"
```

> Imatinib (CHEMBL941) retorna ~700 trials e o sync leva ~20s. O endpoint cacheia tudo localmente — chamadas seguintes ao GET são instantâneas.

---

## Camada Clinical Trials — bulk populate (modo cirúrgico)

Embora o `populate.py` já cubra Clinical Trials na etapa 7, o script `populate_clinical_trials.py` continua existindo para situações em que você quer **só** essa camada — sem rodar o resto do pipeline:

```powershell
# Teste rápido com 5 compostos
python scripts/populate_clinical_trials.py --limit 5

# Rodar tudo (com pausa de 0.5s entre compostos — default)
python scripts/populate_clinical_trials.py

# Pausa maior pra ser educado com a CT.gov
python scripts/populate_clinical_trials.py --sleep 1.0

# Retomar do meio (caiu? pula quem já tem trials cacheados)
python scripts/populate_clinical_trials.py --skip-synced

# Retomar a partir de um chembl_id específico
python scripts/populate_clinical_trials.py --start-from CHEMBL2000

# Só um composto, forçando o nome de busca
python scripts/populate_clinical_trials.py --only CHEMBL941 --drug-name imatinib

# Ver o que seria processado, sem chamar a CT.gov
python scripts/populate_clinical_trials.py --dry-run --limit 20
```

> Cada composto roda em **transação isolada** — erro em um não derruba o batch.
> Compostos com nome IUPAC (ex: `1,2,3,4-TETRAHYDROISOQUINOLINE`) tipicamente retornam 0 trials e são contados como "Sem trials" no resumo final — não é erro.
>
> Para uma base com ~50 compostos, contar ~10-20 minutos (depende dos drugs populares como aspirin/imatinib que têm centenas de trials cada).
>
> **Quando usar esse script vs `populate.py`?** Use `populate.py` no fluxo normal. Use `populate_clinical_trials.py` quando: (a) quer só trials sem re-checar metadata/ADMET/bioact, (b) precisa do `--start-from` pra retomar de um ponto específico, ou (c) quer testar um composto com `--drug-name` override.

---

## Migrar tabelas novas pro Supabase

O `migrate_to_supabase.py` já inclui todas as tabelas das migrations 0004–0007 na ordem correta de FK (compounds → compound_synonyms/atc/admet/bioact/ind/mec/articles/clinical_trials → target_components → target_xrefs). Não há passo extra — basta rodar como antes:

```powershell
$env:DATABASE_URL = "postgresql://postgres.xxx:senha@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"
python migrate_to_supabase.py
```

> Se você só quer migrar uma camada específica (sem mexer no resto), use o flag `--only`:
> ```powershell
> python migrate_to_supabase.py --only compound_synonyms --only compound_atc
> python migrate_to_supabase.py --only target_components --only target_xrefs
> ```

---

## Resumo visual dos terminais

| Terminal | O que roda |
|----------|-----------|
| Terminal 1 | `uvicorn api:app --reload --port 8000` (API) |
| Terminal 2 | `streamlit run dashboard.py` (Dashboard) |
| Terminal 3 | `npm run dev` dentro de `frontend/` (Frontend web) |

---

## Comandos úteis de manutenção

```powershell
# Reprocessar todos os dados do zero (ignora cache incremental)
python populate.py --force

# Pular etapas pesadas
python populate.py --skip-pubmed
python populate.py --skip-trials
python populate.py --skip-pubmed --skip-trials

# Rodar apenas um composto específico
python populate.py --only CHEMBL25

# Adicionar um composto à execução padrão
python populate.py --add CHEMBL941

# Só estrutura e ADMET (rápido, pula bioact/ind/mec/pubmed/trials/targets_enrich)
python populate.py --only-compounds

# Backfill cirúrgico (não roda o pipeline completo)
python scripts/backfill_compound_metadata.py
python scripts/backfill_bioactivity_enrich.py
python scripts/backfill_target_enrich.py

# Ver status das views materializadas
python scripts/refresh.py --status

# Verificar integridade do banco em seção específica
python scripts/validate_db.py --section compounds

# Rodar os testes unitários
pytest tests/ -v

# Derrubar e recriar o banco do zero (apaga todos os dados)
docker compose down -v
docker compose up -d
```

---

## Descobrir novos compostos com o Scraper

O scraper varre uma faixa de IDs numéricos do ChEMBL (ex: CHEMBL10000 até CHEMBL15000), filtra apenas os que têm nome definido (`pref_name`) e os insere na tabela `seed_compounds`. Depois disso, basta rodar `python populate.py` normalmente — ele pega os novos IDs automaticamente.

### Comandos

```powershell
# Varrer IDs de CHEMBL10000 até CHEMBL15000 (faixa básica de exemplo)
python -m populate.scraper --start 10000 --end 15000

# Varrer e atribuir uma categoria específica aos compostos encontrados
python -m populate.scraper --start 10000 --end 15000 --category "Oncologia"

# Varrer e também exportar um CSV com o resultado (compatível com o scraper antigo)
python -m populate.scraper --start 10000 --end 15000 --export-csv compostos.csv

# Reduzir a velocidade das requisições (útil se a API do ChEMBL estiver lenta)
python -m populate.scraper --start 1 --end 15000 --sleep 0.2
```

### Fluxo completo ao usar o scraper

```powershell
# 1. Descobrir novos compostos e inserir na seed_compounds
python -m populate.scraper --start 10000 --end 15000
python -m populate.scraper --start 30001 --end 40000 --sleep 0.2

# 2. Popular os dados completos (metadata, ADMET, bioact, mec, PubMed, trials, targets)
python populate.py

# 3. Atualizar as views
python scripts/refresh.py
```

> O scraper usa `ON CONFLICT DO NOTHING` — rodar duas vezes na mesma faixa é seguro e não duplica dados nem sobrescreve categorias editadas manualmente.

---

## Banco de dados — Local ou Supabase?

O projeto suporta dois fluxos. Escolha o que faz mais sentido para você:

---

### Fluxo 1 — Local primeiro, Supabase depois (padrão do guia acima)

Sem nenhuma variável de ambiente definida, o projeto conecta automaticamente no banco local do Docker (`localhost:5432 / admin / admin123`).

Depois que o banco local estiver populado, você copia tudo para o Supabase com um único comando:

```powershell
$env:DATABASE_URL = "postgresql://postgres.xxx:senha@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"
python migrate_to_supabase.py
```

> O `migrate_to_supabase.py` conecta nos **dois bancos ao mesmo tempo** e copia tabela por tabela do local para o Supabase, respeitando a ordem das chaves estrangeiras.

---

### Fluxo 2 — Direto no Supabase (sem Docker)

Se você já tem a URL do Supabase e não quer usar o banco local, defina a variável **antes de qualquer comando** e pule o Docker completamente:

```powershell
$env:DATABASE_URL = "postgresql://postgres.xxx:senha@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"

alembic upgrade head                    # cria as tabelas no Supabase (todas as migrations)
python populate.py                      # popula direto no Supabase
python scripts/refresh.py              # atualiza views no Supabase
uvicorn api:app --reload --port 8000   # API conecta no Supabase
```

> Nesse fluxo você pula os Passos 5 e 6 do guia e não precisa do `migrate_to_supabase.py`.

---

### Resumo de qual fluxo usar

| Situação | Fluxo recomendado |
|----------|------------------|
| Quero testar localmente antes de subir | Fluxo 1 — siga o guia completo, migre depois |
| Já tenho o banco local populado e quero subir pro Supabase | Fluxo 1 — rode só o `migrate_to_supabase.py` |
| Quero usar o Supabase desde o início, sem Docker | Fluxo 2 — defina `DATABASE_URL` e pule o Docker |

---

## Problemas comuns

| Erro | Causa provável | Solução |
|------|---------------|---------|
| `tabela seed_compounds não existe` | Migration `0002_seed_compounds` não aplicada | Rode o Passo 6 |
| `coluna "molecule_type" não existe` (ou similar) | Migrations 0004–0007 não aplicadas | Rode `alembic upgrade head` |
| `relation "compound_synonyms" does not exist` | Migration `0004_compound_metadata` faltando | Idem |
| `relation "target_components" does not exist` | Migration `0006_target_enrich` faltando | Idem |
| `connection refused` na porta 5432 | Docker não está rodando | Rode o Passo 5 |
| `relation "clinical_trials" does not exist` | Migration `0003_clinical_trials` faltando | Veja "Atualizando após git pull" |
| `502 Falha consultando ClinicalTrials.gov` | Rede / API da CT.gov fora OU WAF temporariamente bloqueando | Cliente já tenta 3x com backoff de 5s/10s/20s; se ainda assim falhar, espere alguns minutos e tente de novo. No `populate.py`, falhas de CT.gov não derrubam o composto — vai pra warning e segue. |
| `ModuleNotFoundError: No module named 'populate'` | Python não encontra a raiz do projeto ao rodar scripts da pasta `scripts/` | Já corrigido — veja nota abaixo |
| `ModuleNotFoundError` (outro) | Ambiente virtual não ativo | Ative o `.venv` (Passo 3) |
| `uvicorn: command not found` | Dependências não instaladas | Rode o Passo 4 |
| Frontend não carrega dados | API não está rodando | Rode o Passo 10 |
| pChEMBL/gene symbol não aparecem no frontend | Backfill das migrations 0005/0006 não rodado | `python populate.py` (cuida automaticamente) ou os scripts de backfill correspondentes |

### Nota — `ModuleNotFoundError: No module named 'populate'`

Esse erro acontecia ao rodar qualquer script da pasta `scripts/` (`validate_db.py`, `refresh.py`, `backfill_*.py`) porque o Python adicionava só a pasta `scripts/` ao path — e o pacote `populate` fica na raiz do projeto.

**Já foi corrigido** em todos os scripts. A linha abaixo foi adicionada no topo de cada script, antes de qualquer import do projeto:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

Isso sobe um nível (`scripts/` → raiz) e registra a raiz no path do Python antes dos imports, resolvendo o erro. Não é necessário fazer nada — os scripts já funcionam com `python scripts/validate_db.py` a partir da raiz do projeto.
