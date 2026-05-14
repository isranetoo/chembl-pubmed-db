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

> - `stamp 0001_baseline`: marca o schema inicial como já aplicado **sem executar SQL** (o Docker já criou as tabelas)
> - `upgrade head`: aplica as migrations restantes, como a tabela `seed_compounds` com 51 compostos padrão
>
> Pular esse passo faz o `populate.py` falhar com erro de "tabela seed_compounds não existe".

---

## Passo 7 — Popular o banco com dados do ChEMBL e PubMed

```powershell
python populate.py
```

> Busca dados reais na internet e salva no banco:
> - Compostos, estruturas químicas e propriedades ADMET do **ChEMBL**
> - Bioatividades, targets, indicações e mecanismos de ação
> - Artigos científicos do **PubMed**
>
> Pode demorar alguns minutos dependendo da conexão. Roda de forma incremental (não reprocessa o que já está completo).

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
# Reprocessar todos os dados do zero
python populate.py --force

# Pular artigos do PubMed (mais rápido)
python populate.py --skip-pubmed

# Rodar apenas um composto específico
python populate.py --only CHEMBL25

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
python -m populate.scraper --start 10000 --end 15000 --sleep 0.2
```

### Fluxo completo ao usar o scraper

```powershell
# 1. Descobrir novos compostos e inserir na seed_compounds
python -m populate.scraper --start 10000 --end 15000

# 2. Popular os dados completos (ADMET, bioatividades, mecanismos, PubMed)
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

alembic upgrade head                    # cria as tabelas no Supabase
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
| `tabela seed_compounds não existe` | Migration não aplicada | Rode o Passo 6 |
| `connection refused` na porta 5432 | Docker não está rodando | Rode o Passo 5 |
| `ModuleNotFoundError: No module named 'populate'` | Python não encontra a raiz do projeto ao rodar scripts da pasta `scripts/` | Já corrigido — veja nota abaixo |
| `ModuleNotFoundError` (outro) | Ambiente virtual não ativo | Ative o `.venv` (Passo 3) |
| `uvicorn: command not found` | Dependências não instaladas | Rode o Passo 4 |
| Frontend não carrega dados | API não está rodando | Rode o Passo 10 |

### Nota — `ModuleNotFoundError: No module named 'populate'`

Esse erro acontecia ao rodar qualquer script da pasta `scripts/` (`validate_db.py`, `refresh.py`, `backfill_abstracts.py`) porque o Python adicionava só a pasta `scripts/` ao path — e o pacote `populate` fica na raiz do projeto.

**Já foi corrigido** nos três arquivos. A linha abaixo foi adicionada no topo de cada script, antes de qualquer import do projeto:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

Isso sobe um nível (`scripts/` → raiz) e registra a raiz no path do Python antes dos imports, resolvendo o erro. Não é necessário fazer nada — os scripts já funcionam com `python scripts/validate_db.py` a partir da raiz do projeto.
