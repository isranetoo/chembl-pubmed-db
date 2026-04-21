"""
validate_db.py
--------------
Verifica a integridade e completude dos dados no banco.
Imprime um relatório de saúde por seção e retorna exit code 1
se houver problemas críticos.

Uso:
    python validate_db.py               # relatório completo
    python validate_db.py --section compounds
    python validate_db.py --section articles
    python validate_db.py --section indications
    python validate_db.py --section admet
    python validate_db.py --section relations
    python validate_db.py --section views
    python validate_db.py --fail-fast   # para no primeiro problema crítico
"""

import argparse
import logging
import sys
from dataclasses import dataclass, field
from typing import Optional

import psycopg2
import psycopg2.extras

from populate.config import DB_CONFIG

log = logging.getLogger(__name__)

# ============================================================
# Estrutura de resultado
# ============================================================

@dataclass
class Check:
    name:     str
    status:   str          # "OK" | "WARN" | "FAIL"
    detail:   str
    critical: bool = False # FAIL crítico → exit code 1

@dataclass
class Section:
    title:  str
    checks: list = field(default_factory=list)

    @property
    def has_fail(self) -> bool:
        return any(c.status == "FAIL" for c in self.checks)

    @property
    def has_warn(self) -> bool:
        return any(c.status == "WARN" for c in self.checks)

    @property
    def summary(self) -> str:
        ok   = sum(1 for c in self.checks if c.status == "OK")
        warn = sum(1 for c in self.checks if c.status == "WARN")
        fail = sum(1 for c in self.checks if c.status == "FAIL")
        return f"OK:{ok}  WARN:{warn}  FAIL:{fail}"


# ============================================================
# Helpers de formatação
# ============================================================

ICONS = {"OK": "✓", "WARN": "!", "FAIL": "✗"}
SEP   = "─" * 58

def _print_section(section: Section) -> None:
    icon = "✗" if section.has_fail else ("!" if section.has_warn else "✓")
    print(f"\n{SEP}")
    print(f" {icon}  {section.title.upper()}  [{section.summary}]")
    print(SEP)
    for c in section.checks:
        i = ICONS[c.status]
        print(f"  {i}  {c.name}")
        if c.detail:
            for line in c.detail.split("\n"):
                print(f"       {line}")

def _ok(name: str, detail: str = "") -> Check:
    return Check(name, "OK", detail)

def _warn(name: str, detail: str = "") -> Check:
    return Check(name, "WARN", detail)

def _fail(name: str, detail: str = "", critical: bool = False) -> Check:
    return Check(name, "FAIL", detail, critical=critical)


# ============================================================
# Checks por seção
# ============================================================

def check_compounds(cur) -> Section:
    sec = Section("Compostos")

    # Total
    cur.execute("SELECT COUNT(*) FROM compounds")
    total = cur.fetchone()[0]
    if total == 0:
        sec.checks.append(_fail("Total de compostos", "Banco vazio — rode populate.py", critical=True))
        return sec
    sec.checks.append(_ok("Total de compostos", f"{total} compostos"))

    # Sem ADMET
    cur.execute("""
        SELECT c.chembl_id, c.name
        FROM compounds c
        LEFT JOIN admet_properties a ON a.compound_id = c.id
        WHERE a.id IS NULL
        ORDER BY c.name
    """)
    rows = cur.fetchall()
    if rows:
        lista = ", ".join(f"{r[1]} ({r[0]})" for r in rows[:5])
        extra = f" e mais {len(rows)-5}" if len(rows) > 5 else ""
        sec.checks.append(_warn(
            f"Compostos sem ADMET ({len(rows)})",
            f"{lista}{extra}\n→ rode: python populate.py --force"
        ))
    else:
        sec.checks.append(_ok("Todos os compostos têm ADMET"))

    # Sem bioatividades
    cur.execute("""
        SELECT c.chembl_id, c.name
        FROM compounds c
        WHERE NOT EXISTS (SELECT 1 FROM bioactivities b WHERE b.compound_id = c.id)
        ORDER BY c.name
    """)
    rows = cur.fetchall()
    if rows:
        lista = ", ".join(r[1] for r in rows[:5])
        extra = f" e mais {len(rows)-5}" if len(rows) > 5 else ""
        sec.checks.append(_warn(
            f"Compostos sem bioatividades ({len(rows)})",
            f"{lista}{extra}"
        ))
    else:
        sec.checks.append(_ok("Todos os compostos têm bioatividades"))

    # Sem indicações
    cur.execute("""
        SELECT c.chembl_id, c.name
        FROM compounds c
        WHERE NOT EXISTS (SELECT 1 FROM indications i WHERE i.compound_id = c.id)
        ORDER BY c.name
    """)
    rows = cur.fetchall()
    if rows:
        lista = ", ".join(r[1] for r in rows[:5])
        extra = f" e mais {len(rows)-5}" if len(rows) > 5 else ""
        sec.checks.append(_warn(
            f"Compostos sem indicações ({len(rows)})",
            f"{lista}{extra}"
        ))
    else:
        sec.checks.append(_ok("Todos os compostos têm indicações"))

    # Sem mecanismos
    cur.execute("""
        SELECT c.chembl_id, c.name
        FROM compounds c
        WHERE NOT EXISTS (SELECT 1 FROM mechanisms m WHERE m.compound_id = c.id)
        ORDER BY c.name
    """)
    rows = cur.fetchall()
    if rows:
        lista = ", ".join(r[1] for r in rows[:5])
        extra = f" e mais {len(rows)-5}" if len(rows) > 5 else ""
        sec.checks.append(_warn(
            f"Compostos sem mecanismos ({len(rows)})",
            f"{lista}{extra}"
        ))
    else:
        sec.checks.append(_ok("Todos os compostos têm mecanismos"))

    # Sem artigos
    cur.execute("""
        SELECT c.chembl_id, c.name
        FROM compounds c
        WHERE NOT EXISTS (SELECT 1 FROM article_compounds ac WHERE ac.compound_id = c.id)
        ORDER BY c.name
    """)
    rows = cur.fetchall()
    if rows:
        lista = ", ".join(r[1] for r in rows[:5])
        extra = f" e mais {len(rows)-5}" if len(rows) > 5 else ""
        sec.checks.append(_warn(
            f"Compostos sem artigos ({len(rows)})",
            f"{lista}{extra}"
        ))
    else:
        sec.checks.append(_ok("Todos os compostos têm artigos"))

    # Campos nulos críticos
    cur.execute("""
        SELECT COUNT(*) FROM compounds
        WHERE name IS NULL OR chembl_id IS NULL OR molecular_formula IS NULL
    """)
    n = cur.fetchone()[0]
    if n > 0:
        sec.checks.append(_fail(f"Compostos com campos críticos nulos ({n})", critical=True))
    else:
        sec.checks.append(_ok("Campos críticos (name, chembl_id, formula) todos preenchidos"))

    return sec


def check_articles(cur) -> Section:
    sec = Section("Artigos")

    cur.execute("SELECT COUNT(*) FROM articles")
    total = cur.fetchone()[0]
    if total == 0:
        sec.checks.append(_warn("Nenhum artigo no banco", "→ rode: python populate.py"))
        return sec
    sec.checks.append(_ok("Total de artigos", f"{total} artigos"))

    # Sem abstract
    cur.execute("SELECT COUNT(*) FROM articles WHERE abstract IS NULL OR abstract = ''")
    n = cur.fetchone()[0]
    pct = round(n / total * 100, 1) if total else 0
    if n > 0:
        level = _fail if pct > 50 else _warn
        sec.checks.append(level(
            f"Artigos sem abstract ({n} / {pct}%)",
            "→ rode: python backfill_abstracts.py"
        ))
    else:
        sec.checks.append(_ok("Todos os artigos têm abstract"))

    # Sem MeSH
    cur.execute("""
        SELECT COUNT(*) FROM articles
        WHERE mesh_terms IS NULL OR mesh_terms = 'null'::jsonb OR mesh_terms = '[]'::jsonb
    """)
    n = cur.fetchone()[0]
    pct = round(n / total * 100, 1) if total else 0
    if n > 0:
        sec.checks.append(_warn(
            f"Artigos sem termos MeSH ({n} / {pct}%)",
            "Normal para artigos mais antigos ou pré-indexados"
        ))
    else:
        sec.checks.append(_ok("Todos os artigos têm termos MeSH"))

    # Sem título
    cur.execute("SELECT COUNT(*) FROM articles WHERE title IS NULL OR title = ''")
    n = cur.fetchone()[0]
    if n > 0:
        sec.checks.append(_fail(f"Artigos sem título ({n})", critical=False))
    else:
        sec.checks.append(_ok("Todos os artigos têm título"))

    # Sem ano
    cur.execute("SELECT COUNT(*) FROM articles WHERE pub_year IS NULL")
    n = cur.fetchone()[0]
    if n > 0:
        sec.checks.append(_warn(f"Artigos sem ano de publicação ({n})"))
    else:
        sec.checks.append(_ok("Todos os artigos têm ano de publicação"))

    # PMIDs duplicados (não deveria existir dado o UNIQUE, mas por segurança)
    cur.execute("""
        SELECT pmid, COUNT(*) AS c FROM articles
        GROUP BY pmid HAVING COUNT(*) > 1
    """)
    rows = cur.fetchall()
    if rows:
        sec.checks.append(_fail(f"PMIDs duplicados ({len(rows)})", critical=True))
    else:
        sec.checks.append(_ok("Nenhum PMID duplicado"))

    # Distribuição por ano
    cur.execute("""
        SELECT pub_year, COUNT(*) AS c
        FROM articles WHERE pub_year IS NOT NULL
        GROUP BY pub_year ORDER BY pub_year DESC LIMIT 5
    """)
    rows = cur.fetchall()
    if rows:
        dist = "  ".join(f"{r[0]}: {r[1]}" for r in rows)
        sec.checks.append(_ok("Anos mais recentes", dist))

    return sec


def check_indications(cur) -> Section:
    sec = Section("Indicações terapêuticas")

    cur.execute("SELECT COUNT(*) FROM indications")
    total = cur.fetchone()[0]
    if total == 0:
        sec.checks.append(_warn("Nenhuma indicação no banco"))
        return sec
    sec.checks.append(_ok("Total de indicações", f"{total} indicações"))

    # Sem mesh_heading
    cur.execute("""
        SELECT COUNT(*) FROM indications
        WHERE mesh_heading IS NULL AND efo_term IS NULL
    """)
    n = cur.fetchone()[0]
    pct = round(n / total * 100, 1) if total else 0
    if n > 0:
        sec.checks.append(_warn(
            f"Indicações sem mesh_heading nem efo_term ({n} / {pct}%)",
            "Entradas com apenas IDs, sem nome legível"
        ))
    else:
        sec.checks.append(_ok("Todas as indicações têm nome (MeSH ou EFO)"))

    # Sem mesh_heading mas com efo_term (parcial)
    cur.execute("""
        SELECT COUNT(*) FROM indications
        WHERE mesh_heading IS NULL AND efo_term IS NOT NULL
    """)
    n = cur.fetchone()[0]
    if n > 0:
        sec.checks.append(_ok(
            f"Indicações só com EFO (sem MeSH): {n}",
            "Normal — ChEMBL nem sempre fornece ambos"
        ))

    # Distribuição por fase clínica
    cur.execute("""
        SELECT
            CASE max_phase
                WHEN 4   THEN 'Aprovado (4)'
                WHEN 3   THEN 'Fase 3'
                WHEN 2   THEN 'Fase 2'
                WHEN 1   THEN 'Fase 1'
                WHEN 0.5 THEN 'Early Phase 1'
                ELSE          'Pré-clínico / ?'
            END AS fase,
            COUNT(*) AS n
        FROM indications
        GROUP BY max_phase
        ORDER BY max_phase DESC NULLS LAST
    """)
    rows = cur.fetchall()
    dist = "  ".join(f"{r[0]}: {r[1]}" for r in rows)
    sec.checks.append(_ok("Distribuição por fase", dist))

    # drugind_id duplicados
    cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT drugind_id FROM indications
            GROUP BY drugind_id HAVING COUNT(*) > 1
        ) t
    """)
    n = cur.fetchone()[0]
    if n > 0:
        sec.checks.append(_fail(f"drugind_ids duplicados ({n})", critical=True))
    else:
        sec.checks.append(_ok("Nenhum drugind_id duplicado"))

    return sec


def check_admet(cur) -> Section:
    sec = Section("Propriedades ADMET")

    cur.execute("SELECT COUNT(*) FROM admet_properties")
    total = cur.fetchone()[0]
    if total == 0:
        sec.checks.append(_warn("Nenhum dado ADMET no banco"))
        return sec
    sec.checks.append(_ok("Total de registros ADMET", f"{total} compostos"))

    # Campos nulos por coluna
    campos = [
        ("alogp",          "ALogP"),
        ("psa",            "PSA"),
        ("qed_weighted",   "QED"),
        ("num_ro5_violations", "Violações Ro5"),
        ("mw_freebase",    "MW freebase"),
    ]
    for col, label in campos:
        cur.execute(f"SELECT COUNT(*) FROM admet_properties WHERE {col} IS NULL")
        n = cur.fetchone()[0]
        pct = round(n / total * 100, 1) if total else 0
        if n == total:
            sec.checks.append(_fail(
                f"{label}: todos nulos",
                "Coluna completamente vazia — verifique fetch_compound"
            ))
        elif n > 0:
            sec.checks.append(_warn(f"{label}: {n} nulos ({pct}%)"))
        else:
            sec.checks.append(_ok(f"{label}: sem nulos"))

    # Resumo de druglikeness
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE num_ro5_violations = 0) AS lipinski_ok,
            COUNT(*) FILTER (WHERE qed_weighted >= 0.5)    AS qed_ok,
            ROUND(AVG(qed_weighted)::numeric, 3)           AS avg_qed,
            ROUND(AVG(alogp)::numeric, 2)                  AS avg_alogp
        FROM admet_properties
    """)
    row = cur.fetchone()
    if row and row[0] is not None:
        sec.checks.append(_ok(
            "Resumo de druglikeness",
            f"Lipinski OK: {row[0]}/{total}  |  "
            f"QED≥0.5: {row[1]}/{total}  |  "
            f"QED médio: {row[2]}  |  aLogP médio: {row[3]}"
        ))

    return sec


def check_relations(cur) -> Section:
    sec = Section("Integridade relacional")

    checks_fk = [
        ("bioactividades → compounds",
         "SELECT COUNT(*) FROM bioactivities b WHERE NOT EXISTS "
         "(SELECT 1 FROM compounds c WHERE c.id = b.compound_id)"),
        ("bioatividades → targets",
         "SELECT COUNT(*) FROM bioactivities b WHERE NOT EXISTS "
         "(SELECT 1 FROM targets t WHERE t.id = b.target_id)"),
        ("indicações → compounds",
         "SELECT COUNT(*) FROM indications i WHERE NOT EXISTS "
         "(SELECT 1 FROM compounds c WHERE c.id = i.compound_id)"),
        ("mecanismos → compounds",
         "SELECT COUNT(*) FROM mechanisms m WHERE NOT EXISTS "
         "(SELECT 1 FROM compounds c WHERE c.id = m.compound_id)"),
        ("article_compounds → articles",
         "SELECT COUNT(*) FROM article_compounds ac WHERE NOT EXISTS "
         "(SELECT 1 FROM articles a WHERE a.id = ac.article_id)"),
        ("article_compounds → compounds",
         "SELECT COUNT(*) FROM article_compounds ac WHERE NOT EXISTS "
         "(SELECT 1 FROM compounds c WHERE c.id = ac.compound_id)"),
        ("admet_properties → compounds",
         "SELECT COUNT(*) FROM admet_properties a WHERE NOT EXISTS "
         "(SELECT 1 FROM compounds c WHERE c.id = a.compound_id)"),
    ]

    for label, query in checks_fk:
        cur.execute(query)
        n = cur.fetchone()[0]
        if n > 0:
            sec.checks.append(_fail(f"FK quebrada: {label} ({n} órfãos)", critical=True))
        else:
            sec.checks.append(_ok(f"FK OK: {label}"))

    # Artigos sem vínculo com nenhum composto
    cur.execute("""
        SELECT COUNT(*) FROM articles a
        WHERE NOT EXISTS (SELECT 1 FROM article_compounds ac WHERE ac.article_id = a.id)
    """)
    n = cur.fetchone()[0]
    if n > 0:
        sec.checks.append(_warn(f"Artigos sem vínculo a nenhum composto: {n}"))
    else:
        sec.checks.append(_ok("Todos os artigos vinculados a ao menos um composto"))

    return sec


def check_views(cur) -> Section:
    sec = Section("Views materializadas")

    views = [
        ("mv_compound_profile",  "profile"),
        ("mv_compound_articles", "articles"),
        ("mv_compound_full",     "full"),
    ]

    for view_name, alias in views:
        try:
            cur.execute(f"SELECT COUNT(*), MAX(refreshed_at) FROM {view_name}")
            row = cur.fetchone()
            count    = row[0] if row else 0
            updated  = row[1].strftime("%Y-%m-%d %H:%M") if row and row[1] else "nunca"

            if count == 0:
                sec.checks.append(_warn(
                    f"{view_name}: vazia",
                    f"→ rode: python refresh.py --view {alias}"
                ))
            else:
                sec.checks.append(_ok(
                    f"{view_name}: {count} linhas",
                    f"Atualizada em: {updated}"
                ))
        except psycopg2.errors.UndefinedTable:
            sec.checks.append(_warn(
                f"{view_name}: não existe",
                "→ aplique: init/07_materialized_views.sql"
            ))
            cur.connection.rollback()

    return sec


# ============================================================
# Runner
# ============================================================

SECTION_MAP = {
    "compounds":   check_compounds,
    "articles":    check_articles,
    "indications": check_indications,
    "admet":       check_admet,
    "relations":   check_relations,
    "views":       check_views,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="validate_db.py",
        description="Relatório de saúde do banco ChEMBL+PubMed.",
    )
    parser.add_argument(
        "--section",
        choices=list(SECTION_MAP.keys()),
        default=None,
        help="Rodar apenas uma seção específica.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Para na primeira seção com FAIL crítico.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    cur  = conn.cursor()

    sections_to_run = (
        {args.section: SECTION_MAP[args.section]}
        if args.section
        else SECTION_MAP
    )

    print(f"\n{'═' * 58}")
    print(f"  RELATÓRIO DE SAÚDE — chembl_pubmed")
    print(f"{'═' * 58}")

    has_critical = False
    all_sections = []

    for name, fn in sections_to_run.items():
        try:
            section = fn(cur)
        except Exception as exc:
            section = Section(name)
            section.checks.append(_fail(f"Erro ao rodar checks: {exc}", critical=True))

        all_sections.append(section)
        _print_section(section)

        if section.has_fail:
            crit = any(c.critical for c in section.checks if c.status == "FAIL")
            if crit:
                has_critical = True
                if args.fail_fast:
                    print(f"\n  [fail-fast] Parando após FAIL crítico em '{section.title}'.")
                    break

    # Resumo final
    total_ok   = sum(sum(1 for c in s.checks if c.status == "OK")   for s in all_sections)
    total_warn = sum(sum(1 for c in s.checks if c.status == "WARN") for s in all_sections)
    total_fail = sum(sum(1 for c in s.checks if c.status == "FAIL") for s in all_sections)

    print(f"\n{'═' * 58}")
    print(f"  RESUMO FINAL")
    print(f"  ✓ OK: {total_ok}   ! WARN: {total_warn}   ✗ FAIL: {total_fail}")
    print(f"{'═' * 58}\n")

    cur.close()
    conn.close()

    if has_critical:
        sys.exit(1)


if __name__ == "__main__":
    main()