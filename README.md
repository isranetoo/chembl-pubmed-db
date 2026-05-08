# chembl-pubmed-db

Repositório para montar uma base PostgreSQL que cruza dados do **ChEMBL** e do **PubMed**, com API FastAPI, dashboard Streamlit e frontend React/Vite.

## Estrutura do repositório

```txt
chembl-pubmed-db/
├── api.py                         # API FastAPI
├── dashboard.py                   # Dashboard Streamlit
├── populate.py                    # Atalho para populate/populate.py
├── refresh.py                     # Refresh de views materializadas
├── validate_db.py                 # Validação de integridade do banco
├── scheduler.py                   # Atalho para populate/scheduler.py
├── migrate_to_supabase.py         # Atalho para populate/migrate_to_supabase.py
├── populate/                      # Clientes, ingestão, DB helpers e scheduler
├── database/init/                 # SQL de criação/enriquecimento do schema
├── config/pgadmin_servers.json    # Configuração do pgAdmin
├── frontend/                      # App React/Vite
├── docs/                          # Documentação complementar
└── tests/                         # Testes unitários
```

## Subir banco local

```bash
docker compose up -d
```

O Compose monta os scripts de schema de `database/init/` no PostgreSQL e carrega a configuração do pgAdmin de `config/pgadmin_servers.json`.

## Popular dados

```bash
# Comportamento padrão: incremental
python populate.py

# Adicionar um composto que não está na lista
python populate.py --add CHEMBL941

# Adicionar vários compostos
python populate.py --add CHEMBL941 --add CHEMBL192

# Rodar apenas compostos específicos
python populate.py --only CHEMBL25 --only CHEMBL521

# Só estrutura + ADMET, pulando bioatividades/indicações/mecanismos/PubMed
python populate.py --only-compounds

# Pular só o PubMed
python populate.py --skip-pubmed

# Forçar reprocessamento de compostos já completos
python populate.py --force

# Ver todos os flags disponíveis
python populate.py --help
```

## Banco de dados e manutenção

```bash
# Atualizar as views materializadas
python refresh.py
python refresh.py --view full
python refresh.py --status

# Validar integridade/completude
python validate_db.py
python validate_db.py --section compounds
python validate_db.py --section relations
python validate_db.py --fail-fast

# Migrar para Supabase ou outro PostgreSQL remoto
python migrate_to_supabase.py
python migrate_to_supabase.py --target-url "postgresql://..."
```

## Agendamento do pipeline

```bash
# Testar o pipeline agora, sem agendar
python scheduler.py --run-now

# Testar a cada 2 horas em modo dev
python scheduler.py --interval-hours 2

# Produção: toda segunda às 03:00
python scheduler.py

# Toda sexta às 06:00, pulando validate
python scheduler.py --day fri --hour 6 --skip-validate

# Forçar reprocessamento no próximo ciclo
python scheduler.py --populate-args "--force"
```

## API, dashboard e frontend

```bash
# API FastAPI
uvicorn api:app --reload --port 8000

# Dashboard Streamlit
streamlit run dashboard.py

# Frontend React/Vite
cd frontend
npm install
npm run dev
```

### Exemplos de chamadas da API

```bash
curl "localhost:8000/compounds?min_phase=4&min_qed=0.6&sort_by=qed&sort_order=desc"
curl "localhost:8000/compounds/CHEMBL941/indications?min_phase=4"
curl "localhost:8000/search?q=inflammation+cox"
curl "localhost:8000/articles?q=aspirin&pub_type=Review"
```

## Configuração de conexão

A conexão é resolvida nesta ordem:

1. `DATABASE_URL` para Supabase/PaaS.
2. Variáveis individuais: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_SSLMODE`.
3. Defaults do Docker local: `localhost:5432`, banco `chembl_pubmed`, usuário `admin`, senha `admin123`.

```bash
# Linux/macOS
DATABASE_URL="postgresql://..." python populate.py

# Windows PowerShell
$env:DATABASE_URL="postgresql://postgres.xxx:senha@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"
python populate.py
```

## Testes

```bash
pytest tests/ -v
pytest tests/ -v -k "chembl"
pytest tests/ -v -k "abstract"
pytest tests/ -v -k "db"
pytest tests/ --tb=short
```
