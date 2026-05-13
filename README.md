# chembl-pubmed-db

`chembl-pubmed-db` cria uma base PostgreSQL local com dados de compostos farmacológicos vindos do **ChEMBL** e artigos científicos vindos do **PubMed**. O projeto também oferece:

- uma **API FastAPI** para consultar compostos, alvos, artigos, indicações, mecanismos, ADMET e busca full-text;
- um **dashboard Streamlit** para exploração rápida dos dados;
- um **frontend React/Vite** para navegar pela base via navegador;
- scripts para **popular**, **validar**, **atualizar views**, **agendar pipeline** e **migrar para Supabase/outro PostgreSQL**.

---

## 1. O que cada parte faz

| Parte | Arquivo/pasta | O que faz |
| --- | --- | --- |
| Banco PostgreSQL | `docker-compose.yml` + `database/init/` | Sobe PostgreSQL, pgAdmin e cria as tabelas/views usando os SQLs de inicialização. |
| Ingestão de dados | `python populate.py` | Busca compostos no ChEMBL, bioatividades, targets, indicações, mecanismos, propriedades ADMET e artigos no PubMed. |
| Refresh de views | `python refresh.py` | Atualiza as views materializadas usadas por consultas consolidadas. |
| Validação | `python validate_db.py` | Verifica se o banco tem dados, integridade de FKs, artigos, ADMET e views. |
| API | `uvicorn api:app --reload --port 8000` | Expõe endpoints HTTP para consumir os dados. |
| Dashboard | `streamlit run dashboard.py` | Abre uma interface Streamlit local para explorar a base. |
| Frontend web | `frontend/` | App React/Vite que consome a API FastAPI. |
| Scheduler | `python scheduler.py` | Roda o pipeline automaticamente em horário configurado. |
| Migração | `python migrate_to_supabase.py` | Copia dados do PostgreSQL local para Supabase ou outro PostgreSQL remoto. |

---

## 2. Estrutura do repositório

```txt
chembl-pubmed-db/
├── api.py                         # API FastAPI
├── dashboard.py                   # Dashboard Streamlit
├── populate.py                    # Comando principal de ingestão
├── refresh.py                     # Atualiza views materializadas
├── validate_db.py                 # Valida saúde/integridade do banco
├── scheduler.py                   # Agenda ou executa o pipeline completo
├── migrate_to_supabase.py         # Migração para PostgreSQL remoto/Supabase
├── populate/                      # Implementação da ingestão e clientes externos
├── database/init/                 # SQLs executados na criação do banco Docker
├── config/pgadmin_servers.json    # Configuração automática do pgAdmin
├── frontend/                      # Frontend React/Vite
├── docs/                          # Documentação complementar
├── tests/                         # Testes unitários
└── requirements.txt               # Dependências Python
```

---

## 3. Pré-requisitos

Instale antes de rodar:

- **Python 3.11+**;
- **Docker** e **Docker Compose**;
- **Node.js 18+** e `npm` se quiser rodar o frontend React;
- acesso à internet para baixar dados do ChEMBL/PubMed e instalar dependências.

---

## 4. Passo a passo completo para rodar localmente

### Passo 1 — Entrar na pasta do projeto

```bash
cd chembl-pubmed-db
```

### Passo 2 — Criar e ativar ambiente Python

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Passo 3 — Instalar dependências Python

```bash
pip install -r requirements.txt
```

### Passo 4 — Subir PostgreSQL e pgAdmin

```bash
docker compose up -d
```

Esse comando sobe:

- PostgreSQL em `localhost:5432`;
- pgAdmin em `http://localhost:5050`;
- login do pgAdmin: `israneto20@gmail.com`;
- senha do pgAdmin: `admin123`;
- banco padrão `chembl_pubmed`;
- usuário `admin`;
- senha `admin123`.

O Docker executa automaticamente os arquivos em `database/init/` quando o volume do banco é criado pela primeira vez.

> Se você já tinha subido o banco antes e quer recriar tudo do zero, use `docker compose down -v` e depois `docker compose up -d`. Atenção: isso apaga os dados locais do volume Docker.

### Passo 4.5 — Registrar o baseline e aplicar migrations restantes

O Docker já criou o schema do baseline (01..08) via `database/init/*.sql`, então **marque só o baseline como aplicado** e depois rode as migrations seguintes (atualmente: a tabela `seed_compounds` da migration 0002):

```bash
alembic stamp 0001_baseline
alembic upgrade head
```

- `stamp 0001_baseline` grava a versão do baseline na tabela `alembic_version` **sem executar SQL** — evita recriar tabelas que já existem.
- `upgrade head` aplica as migrations criadas depois do baseline (cria `seed_compounds` e popula com 51 compostos).

Pular `upgrade head` faz `populate.py` falhar com erro claro: "Tabela `seed_compounds` não existe". Consulte a [seção 13](#13-migrations-com-alembic) para o fluxo completo.

### Passo 5 — Popular o banco com ChEMBL + PubMed

```bash
python populate.py
```

A lista padrão de compostos vem da tabela `seed_compounds` (ver [seção 15](#15-gerenciar-a-lista-de-compostos-populares)). Por padrão, o comando roda de forma incremental e evita reprocessar compostos que já estão completos — use `--force` para forçar.

### Passo 6 — Validar se os dados foram carregados corretamente

```bash
python validate_db.py
```

Se quiser parar no primeiro erro crítico:

```bash
python validate_db.py --fail-fast
```

### Passo 7 — Atualizar views materializadas

```bash
python refresh.py
```

Para ver o status das views:

```bash
python refresh.py --status
```

### Passo 8 — Rodar a API

```bash
uvicorn api:app --reload --port 8000
```

Depois abra:

- API: `http://localhost:8000`;
- documentação Swagger: `http://localhost:8000/docs`;
- documentação ReDoc: `http://localhost:8000/redoc`;
- health check: `http://localhost:8000/health`.

### Passo 9 — Rodar o dashboard Streamlit

Em outro terminal, com o ambiente Python ativado:

```bash
streamlit run dashboard.py
```

O Streamlit normalmente abre em `http://localhost:8501`.

### Passo 10 — Rodar o frontend React/Vite

Em outro terminal:

```bash
cd frontend
npm install
npm run dev
```

O Vite normalmente abre em `http://localhost:5173`.

O frontend usa a variável abaixo, já documentada em `frontend/.env.example`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## 5. Comandos principais do `populate.py`

| Comando | Quando usar | O que faz |
| --- | --- | --- |
| `python populate.py` | Uso normal | Popula/atualiza a base de forma incremental com a lista padrão de compostos. |
| `python populate.py --add CHEMBL941` | Adicionar um composto extra | Inclui o composto informado na execução atual. |
| `python populate.py --add CHEMBL941 --add CHEMBL192` | Adicionar vários extras | Repete `--add` para vários ChEMBL IDs. |
| `python populate.py --only CHEMBL25` | Rodar só um composto | Ignora a lista padrão e processa apenas o ID informado. |
| `python populate.py --only CHEMBL25 --only CHEMBL521` | Rodar só alguns compostos | Processa apenas os IDs informados. |
| `python populate.py --only-compounds` | Teste rápido/estrutura | Busca estrutura e ADMET, pulando bioatividades, indicações, mecanismos e PubMed. |
| `python populate.py --skip-pubmed` | Quando PubMed/internet estiver lento | Pula apenas a etapa de artigos PubMed. |
| `python populate.py --force` | Reprocessar tudo | Ignora o cache incremental e reprocessa compostos completos. |
| `python populate.py --help` | Ver ajuda oficial | Mostra todas as opções do comando. |

Exemplos práticos:

```bash
# Processar somente aspirina e ibuprofeno
python populate.py --only CHEMBL25 --only CHEMBL521

# Adicionar imatinib e não buscar PubMed nesta execução
python populate.py --add CHEMBL941 --skip-pubmed

# Reprocessar os dados mesmo se já estiverem completos
python populate.py --force
```

---

## 6. Comandos de manutenção do banco

### Atualizar views

```bash
# Atualizar todas as views materializadas
python refresh.py

# Atualizar apenas uma view específica
python refresh.py --view profile
python refresh.py --view articles
python refresh.py --view full

# Mostrar linhas e data de refresh das views
python refresh.py --status
```

### Validar dados

```bash
# Relatório completo
python validate_db.py

# Rodar apenas uma seção
python validate_db.py --section compounds
python validate_db.py --section articles
python validate_db.py --section indications
python validate_db.py --section admet
python validate_db.py --section relations
python validate_db.py --section views

# Parar no primeiro FAIL crítico
python validate_db.py --fail-fast
```

---

## 7. Endpoints principais da API

Suba a API com:

```bash
uvicorn api:app --reload --port 8000
```

Endpoints úteis:

| Endpoint | O que retorna |
| --- | --- |
| `GET /health` | Status básico da API/banco. |
| `GET /stats` | Métricas gerais para dashboard/frontend. |
| `GET /compounds` | Lista de compostos, com filtros e ordenação. |
| `GET /compounds/{chembl_id}` | Detalhe de um composto. |
| `GET /compounds/{chembl_id}/admet` | Propriedades ADMET do composto. |
| `GET /compounds/{chembl_id}/indications` | Indicações terapêuticas do composto. |
| `GET /compounds/{chembl_id}/mechanisms` | Mecanismos de ação. |
| `GET /compounds/{chembl_id}/bioactivities` | Bioatividades ligadas a targets. |
| `GET /compounds/{chembl_id}/articles` | Artigos PubMed relacionados. |
| `GET /articles` | Lista de artigos. |
| `GET /articles/{pmid}` | Detalhe de um artigo por PMID. |
| `GET /targets` | Lista de targets. |
| `GET /search?q=texto` | Busca full-text em compostos/artigos. |

Exemplos com `curl`:

```bash
# Compostos aprovados com QED alto
curl "http://localhost:8000/compounds?min_phase=4&min_qed=0.6&sort_by=qed&sort_order=desc"

# Indicações aprovadas do Imatinib
curl "http://localhost:8000/compounds/CHEMBL941/indications?min_phase=4"

# Busca full-text unificada
curl "http://localhost:8000/search?q=inflammation+cox"

# Artigos de revisão sobre aspirina
curl "http://localhost:8000/articles?q=aspirin&pub_type=Review"
```

---

## 8. Configuração de banco de dados

A aplicação resolve a conexão nesta ordem:

1. `DATABASE_URL`, útil para Supabase, Railway, Render, Heroku ou outro PaaS;
2. variáveis individuais `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_SSLMODE`;
3. defaults locais do Docker: `localhost:5432`, banco `chembl_pubmed`, usuário `admin`, senha `admin123` — **apenas em desenvolvimento** (ver seção 14).

### Usar Docker local sem variáveis

```bash
python populate.py
```

### Usar `DATABASE_URL` no Linux/macOS

```bash
DATABASE_URL="postgresql://usuario:senha@host:5432/banco?sslmode=require" python populate.py
```

### Usar `DATABASE_URL` no Windows PowerShell

```powershell
$env:DATABASE_URL="postgresql://usuario:senha@host:5432/banco?sslmode=require"
python populate.py
```

### Usar variáveis individuais no Linux/macOS

```bash
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_NAME="chembl_pubmed"
export DB_USER="admin"
export DB_PASSWORD="admin123"
python populate.py
```

---

## 9. Agendar ou rodar pipeline completo

O scheduler executa a sequência:

1. `populate.py`;
2. `refresh.py`;
3. `validate_db.py`.

Comandos:

```bash
# Rodar o pipeline uma vez agora e sair
python scheduler.py --run-now

# Agendar toda segunda às 03:00, padrão do script
python scheduler.py

# Agendar toda sexta às 06:00
python scheduler.py --day fri --hour 6

# Rodar a cada 12 horas, útil para teste/dev
python scheduler.py --interval-hours 12

# Pular validação
python scheduler.py --skip-validate

# Pular refresh das views
python scheduler.py --skip-refresh

# Passar flags extras para populate.py
python scheduler.py --populate-args "--force --add CHEMBL941"
```

---

## 10. Migrar para Supabase ou outro PostgreSQL remoto

Use este fluxo quando o banco local já estiver populado e você quiser copiar os dados para um banco remoto.

### Via variável de ambiente

```bash
export DATABASE_URL="postgresql://usuario:senha@host-remoto:5432/postgres?sslmode=require"
python migrate_to_supabase.py
```

### Via flag

```bash
python migrate_to_supabase.py --target-url "postgresql://usuario:senha@host-remoto:5432/postgres?sslmode=require"
```

### Modo simulação

```bash
python migrate_to_supabase.py --dry-run
```

### Pular criação do schema remoto

```bash
python migrate_to_supabase.py --skip-schema
```

### Migrar apenas algumas tabelas

```bash
python migrate_to_supabase.py --only compounds --only articles
```

---

## 11. Testes e checks

```bash
# Testes unitários
pytest tests/ -v

# Testes filtrados
pytest tests/ -v -k "chembl"
pytest tests/ -v -k "abstract"
pytest tests/ -v -k "db"

# Saída compacta
pytest tests/ --tb=short

# Verificar sintaxe/imports Python
python -m compileall api.py dashboard.py refresh.py validate_db.py populate.py scheduler.py migrate_to_supabase.py populate tests

# Build do frontend
npm --prefix frontend install
npm --prefix frontend run build
```

---

## 12. Fluxo recomendado para desenvolvimento diário

```bash
# 1. Subir banco
docker compose up -d

# 2. Popular/atualizar dados
python populate.py

# 3. Validar banco
python validate_db.py

# 4. Atualizar views
python refresh.py

# 5. Subir API
uvicorn api:app --reload --port 8000

# 6. Em outro terminal, subir frontend
cd frontend
npm install
npm run dev
```

---

## 13. Migrations com Alembic

A partir do baseline `0001_baseline`, toda alteração de schema deve virar uma migration Alembic. Os arquivos em `database/init/` continuam funcionando para a criação inicial via Docker — o baseline apenas garante que o estado atual fique versionado e que mudanças futuras sejam auditáveis.

### Estrutura

```txt
alembic.ini                          # config
migrations/
├── env.py                           # lê DB_CONFIG de populate/config.py
├── script.py.mako                   # template de novas migrations
└── versions/
    └── 0001_baseline.py             # captura os 8 SQLs de database/init/
```

### Fluxos

**Banco que já tem o schema (criado via `docker compose up -d`)**:

```bash
alembic stamp head   # só marca o baseline como aplicado, NÃO executa SQL
alembic current      # confirma a revisão atual
```

**Banco totalmente vazio (Postgres novo, sem Docker init)**:

```bash
alembic upgrade head # executa os SQLs do baseline em ordem
```

**Criar uma nova migration**:

```bash
alembic revision -m "add table foo"
# edita migrations/versions/<hash>_add_table_foo.py
alembic upgrade head
```

**Reverter a última migration** (não vale para o baseline):

```bash
alembic downgrade -1
```

**Inspeção**:

```bash
alembic current      # versão aplicada no banco
alembic history      # histórico de revisões
alembic heads        # lista heads (deve ser sempre 1)
```

### Apontar para Supabase ou outro PostgreSQL

O mesmo mecanismo do resto do projeto: definir `DATABASE_URL` antes do comando.

```powershell
$env:DATABASE_URL="postgresql://usuario:senha@host:5432/banco?sslmode=require"
alembic upgrade head
```

### Boas práticas

- Toda alteração de schema vira uma migration nova — não edite `0001_baseline.py`.
- O downgrade do baseline está bloqueado (`NotImplementedError`); para zerar tudo, derrube o volume Docker.
- Após escrever uma migration, rode `alembic upgrade head --sql` para inspecionar o SQL gerado antes de aplicar em produção.

---

## 14. Variáveis de ambiente de produção

Para evitar que defaults inseguros vazem para staging/produção, a API e o pipeline aplicam dois gates obrigatórios fora de desenvolvimento.

### `APP_ENV`

Controla qual cenário está ativo. Valores reconhecidos como dev: `development`, `dev`, `local`, `test`. Qualquer outro valor é tratado como produção/staging.

```bash
APP_ENV=production
```

- **Default** (`development`): defaults locais Docker (`localhost`/`admin`/`admin123`) e CORS de `localhost:5173/8501` são aplicados automaticamente.
- **`production`**: a inicialização falha (`RuntimeError`) se `DATABASE_URL` ou `DB_HOST/...` não estiver definida — evita conectar acidentalmente em outro Postgres com a senha conhecida `admin123`.

### `CORS_ALLOW_ORIGINS`

Lista separada por vírgula de origens permitidas pelo middleware CORS.

```bash
CORS_ALLOW_ORIGINS="https://app.example.com,https://admin.example.com"
```

- **Default em dev**: `http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:8501`.
- **Em produção**: a inicialização falha se essa variável não estiver definida — evita publicar a API com `allow_origins=["*"]`.

### Receita mínima para produção

```bash
export APP_ENV=production
export DATABASE_URL="postgresql://usuario:senha@host:5432/banco?sslmode=require"
export CORS_ALLOW_ORIGINS="https://app.example.com"
uvicorn api:app --host 0.0.0.0 --port 8000
```

Se algum dos três faltar, a API recusa subir com mensagem explicando o que falta.

---

## 15. Gerenciar a lista de compostos populares

A lista que o `populate.py` consome por padrão vive na tabela `seed_compounds` (criada pela migration `0002_seed_compounds`). Adicionar, desativar ou reativar um composto é uma operação de banco — não precisa de PR/deploy.

### Estrutura

```sql
SELECT chembl_id, common_name, category, is_active FROM seed_compounds;
```

| Coluna       | Função                                                       |
| ------------ | ------------------------------------------------------------ |
| `chembl_id`  | Identificador no ChEMBL (PK).                                |
| `common_name`| Nome popular usado nos logs e nas buscas PubMed iniciais.    |
| `category`   | Agrupamento terapêutico (Oncologia, Cardiovascular…).        |
| `is_active`  | `populate.py` só lê linhas com `TRUE`.                       |
| `added_at`   | Timestamp automático.                                        |

### Receitas

**Adicionar um composto:**

```sql
INSERT INTO seed_compounds (chembl_id, common_name, category)
VALUES ('CHEMBL999', 'Foo', 'Oncologia');
```

A próxima execução de `python populate.py` já inclui o composto.

**Desativar (sem perder histórico):**

```sql
UPDATE seed_compounds SET is_active = FALSE WHERE chembl_id = 'CHEMBL999';
```

**Reativar:**

```sql
UPDATE seed_compounds SET is_active = TRUE WHERE chembl_id = 'CHEMBL999';
```

**Listar por categoria:**

```sql
SELECT chembl_id, common_name
FROM seed_compounds
WHERE category = 'Oncologia' AND is_active = TRUE
ORDER BY common_name;
```

### Variantes via CLI já existentes

O `populate.py` continua aceitando overrides ad-hoc sem mexer na tabela:

```bash
python populate.py --only CHEMBL25 --only CHEMBL521   # ignora tabela, roda só esses dois
python populate.py --add CHEMBL999                    # adiciona à lista lida da tabela
```

Use a tabela para a lista permanente; use as flags para experimentos pontuais.

