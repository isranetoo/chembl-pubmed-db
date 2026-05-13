"""Atalho de CLI para executar o pipeline de ingestão.

Mantém o comando documentado `python populate.py` enquanto a implementação
fica organizada dentro do pacote `populate`.
"""

from populate.populate import main


if __name__ == "__main__":
    main()
