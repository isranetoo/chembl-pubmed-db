# chembl-pubmed-db

# Comportamento padrão — igual ao anterior, incremental
python populate.py

# Adicionar um composto que não está na lista
python populate.py --add CHEMBL941

# Adicionar vários de uma vez
python populate.py --add CHEMBL941 --add CHEMBL192

# Rodar só compostos específicos
python populate.py --only CHEMBL25 --only CHEMBL521

# Só estrutura + ADMET, pular bioatividades/indicações/mecanismos/PubMed
python populate.py --only-compounds

# Pular só o PubMed (útil quando a internet está lenta)
python populate.py --skip-pubmed

# Forçar re-processo de compostos já completos
python populate.py --force

# Combinar: adicionar novo composto, pular PubMed, forçar os já existentes
python populate.py --add CHEMBL941 --skip-pubmed --force

# Ver todos os flags disponíveis
python populate.py --help

python refresh.py              # atualiza as 3 views
python refresh.py --view full  # atualiza só mv_compound_full
python refresh.py --status     # mostra linhas e horário de refresh

python validate_db.py                      # relatório completo
python validate_db.py --section compounds  # só compostos
python validate_db.py --section relations  # só integridade de FK
python validate_db.py --fail-fast          # para no primeiro FAIL crítico

pytest tests/ -v -k "chembl"    # só ChEMBL
pytest tests/ -v -k "abstract"  # só parsers de abstract
pytest tests/ -v -k "db"        # só banco
pytest tests/ --tb=short        # saída compacta

streamlit run dashboard.py

uvicorn api:app --reload --port 8000

# Compostos aprovados com QED alto
curl "localhost:8000/compounds?min_phase=4&min_qed=0.6&sort_by=qed&sort_order=desc"

# Indicações aprovadas do Imatinib
curl "localhost:8000/compounds/CHEMBL941/indications?min_phase=4"

# Busca full-text unificada
curl "localhost:8000/search?q=inflammation+cox"

# Artigos de revisão sobre aspirina
curl "localhost:8000/articles?q=aspirin&pub_type=Review"

# Modo 1 — DATABASE_URL (Supabase e qualquer PaaS):
bash# Windows PowerShell
$env:DATABASE_URL="postgresql://postgres.xxx:senha@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"
python populate.py

# Linux / macOS

DATABASE_URL="postgresql://..." python populate.py

# Modo 2 — variáveis individuais (outro servidor PostgreSQL):

bash$env:DB_HOST="meu-servidor.com"
$env:DB_PASSWORD="minha_senha"
$env:DB_SSLMODE="require"
python populate.py

# Modo 3 — sem variáveis (Docker local, comportamento anterior):

bashpython populate.py   # usa localhost:5432 / admin / admin123

# supabase
python migrate_to_supabase.py

# Testar o pipeline agora (sem agendar nada)
python scheduler.py --run-now

# Testar a cada 2 horas (modo dev)
python scheduler.py --interval-hours 2

# Produção — toda segunda às 03:00 (deixar rodando em background)
python scheduler.py

# Toda sexta às 06:00, pulando validate
python scheduler.py --day fri --hour 6 --skip-validate

# Forçar re-processo de tudo no próximo ciclo
python scheduler.py --populate-args "--force"