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