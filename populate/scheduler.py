"""
scheduler.py
------------
Executa o pipeline automaticamente toda semana:
  1. populate.py   — busca novos artigos no PubMed (incremental)
  2. refresh.py    — atualiza as views materializadas
  3. validate_db.py— verifica integridade do banco e imprime relatório

Instalação:
    pip install apscheduler

Execução:
    python scheduler.py                      # toda segunda às 03:00
    python scheduler.py --run-now            # roda agora e sai
    python scheduler.py --day fri --hour 6   # toda sexta às 06:00
    python scheduler.py --interval-hours 12  # a cada 12h (dev/teste)

Flags:
    --run-now             Executa o pipeline uma vez imediatamente e sai
    --day DAY             Dia da semana: mon tue wed thu fri sat sun (default: mon)
    --hour HOUR           Hora 0-23 (default: 3)
    --minute MINUTE       Minuto 0-59 (default: 0)
    --interval-hours N    Rodar a cada N horas em vez de semanalmente
    --skip-validate       Pular o validate_db.py
    --skip-refresh        Pular o refresh.py
    --populate-args ARGS  Args extras para o populate.py (ex: '--force')
    --timezone TZ         Fuso horário (default: America/Sao_Paulo)
"""

import argparse
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ============================================================
# Localização dos scripts
# ============================================================

def _find_project_root() -> Path:
    """Sobe a partir do scheduler.py até encontrar populate.py."""
    candidate = Path(__file__).parent.resolve()
    for _ in range(4):
        if (candidate / "populate.py").exists() or (candidate / "populate" / "populate.py").exists():
            return candidate
        candidate = candidate.parent
    return Path(__file__).parent.resolve()


ROOT   = _find_project_root()
PYTHON = sys.executable   # mesmo Python do venv ativo


def _script(name: str) -> Path:
    """Retorna o caminho absoluto de um script, buscando em ROOT e ROOT/populate."""
    for base in [ROOT, ROOT / "populate"]:
        p = base / name
        if p.exists():
            return p
    return ROOT / name   # fallback — deixa o subprocess dar erro claro


# ============================================================
# Pipeline
# ============================================================

def run_step(label: str, cmd: list) -> bool:
    """Executa um subprocesso. Retorna True se OK, False se falhou."""
    log.info(f"  -> {label}")
    log.info(f"     {' '.join(str(c) for c in cmd)}")
    t0 = time.perf_counter()
    try:
        result = subprocess.run(cmd, cwd=str(ROOT))
        elapsed = round(time.perf_counter() - t0, 1)
        if result.returncode == 0:
            log.info(f"  OK {label} concluido em {elapsed}s")
            return True
        else:
            log.error(f"  FAIL {label} (exit {result.returncode}) em {elapsed}s")
            return False
    except Exception as exc:
        log.error(f"  FAIL {label} erro: {exc}")
        return False


def run_pipeline(
    skip_validate:  bool = False,
    skip_refresh:   bool = False,
    populate_args:  str  = "",
) -> bool:
    """
    Executa populate -> refresh -> validate em sequencia.
    Retorna True se tudo OK, False se alguma etapa falhou.
    """
    started = datetime.now()
    log.info("=" * 58)
    log.info(f"PIPELINE INICIADO - {started.strftime('%Y-%m-%d %H:%M:%S')}")
    log.info(f"  Root do projeto : {ROOT}")
    log.info(f"  Python          : {PYTHON}")
    log.info("=" * 58)

    results = {}

    # 1. Populate (incremental - so busca o que falta)
    populate_cmd = [PYTHON, str(_script("populate.py"))]
    if populate_args:
        populate_cmd += populate_args.split()
    results["populate"] = run_step("populate.py", populate_cmd)

    # 2. Refresh das views materializadas
    if not skip_refresh:
        results["refresh"] = run_step(
            "refresh.py",
            [PYTHON, str(_script("refresh.py"))],
        )
    else:
        log.info("  . refresh ignorado (--skip-refresh)")

    # 3. Validacao do banco
    if not skip_validate:
        results["validate"] = run_step(
            "validate_db.py",
            [PYTHON, str(_script("validate_db.py"))],
        )
    else:
        log.info("  . validate_db ignorado (--skip-validate)")

    # Resumo
    elapsed = round((datetime.now() - started).total_seconds())
    ok = all(results.values())

    log.info("=" * 58)
    log.info(f"PIPELINE {'OK' if ok else 'COM ERROS'} - {elapsed}s total")
    for step, success in results.items():
        log.info(f"  {'OK' if success else 'FAIL'} {step}")
    log.info("=" * 58)

    return ok


# ============================================================
# CLI
# ============================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="scheduler.py",
        description="Agenda execucao semanal do pipeline ChEMBL+PubMed.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
exemplos:
  python scheduler.py                        # toda segunda as 03:00
  python scheduler.py --run-now              # roda agora e sai
  python scheduler.py --day fri --hour 6     # toda sexta as 06:00
  python scheduler.py --interval-hours 12    # a cada 12h (dev)
  python scheduler.py --populate-args "--force --add CHEMBL941"
        """,
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Executa o pipeline imediatamente e sai (sem agendar).",
    )
    parser.add_argument(
        "--day",
        default="mon",
        choices=["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        help="Dia da semana (default: mon).",
    )
    parser.add_argument(
        "--hour",
        type=int,
        default=3,
        metavar="0-23",
        help="Hora do dia 0-23 (default: 3).",
    )
    parser.add_argument(
        "--minute",
        type=int,
        default=0,
        metavar="0-59",
        help="Minuto 0-59 (default: 0).",
    )
    parser.add_argument(
        "--interval-hours",
        type=float,
        default=None,
        metavar="N",
        help="Rodar a cada N horas em vez de semanalmente (teste).",
    )
    parser.add_argument(
        "--timezone",
        default="America/Sao_Paulo",
        metavar="TZ",
        help="Fuso horario IANA (default: America/Sao_Paulo).",
    )
    parser.add_argument(
        "--skip-validate",
        action="store_true",
        help="Pular o validate_db.py.",
    )
    parser.add_argument(
        "--skip-refresh",
        action="store_true",
        help="Pular o refresh das views materializadas.",
    )
    parser.add_argument(
        "--populate-args",
        default="",
        metavar="ARGS",
        help="Args extras para o populate.py (ex: '--force').",
    )
    return parser.parse_args()


# ============================================================
# Main
# ============================================================

def main() -> None:
    args = parse_args()

    pipeline_kwargs = {
        "skip_validate": args.skip_validate,
        "skip_refresh":  args.skip_refresh,
        "populate_args": args.populate_args,
    }

    # Modo imediato
    if args.run_now:
        ok = run_pipeline(**pipeline_kwargs)
        sys.exit(0 if ok else 1)

    # Modo agendado (requer APScheduler)
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.triggers.interval import IntervalTrigger
    except ImportError:
        log.error("APScheduler nao instalado. Rode: pip install apscheduler")
        log.info("Alternativa: use --run-now para executar uma vez manualmente.")
        sys.exit(1)

    scheduler = BlockingScheduler(timezone=args.timezone)

    if args.interval_hours:
        trigger = IntervalTrigger(hours=args.interval_hours)
        desc    = f"a cada {args.interval_hours}h"
    else:
        trigger = CronTrigger(
            day_of_week = args.day,
            hour        = args.hour,
            minute      = args.minute,
            timezone    = args.timezone,
        )
        nomes = {
            "mon": "segunda", "tue": "terca",  "wed": "quarta",
            "thu": "quinta",  "fri": "sexta",  "sat": "sabado",
            "sun": "domingo",
        }
        desc = f"toda {nomes[args.day]} as {args.hour:02d}:{args.minute:02d}"

    scheduler.add_job(
        run_pipeline,
        trigger = trigger,
        kwargs  = pipeline_kwargs,
        id      = "chembl_pubmed_pipeline",
        name    = f"Pipeline ChEMBL+PubMed ({desc})",
        misfire_grace_time = 3600,  # tolera ate 1h de atraso
        coalesce           = True,  # nao empilha execucoes perdidas
    )

    log.info(f"Pipeline agendado : {desc}")
    log.info(f"Fuso horario      : {args.timezone}")
    log.info(f"Root do projeto   : {ROOT}")
    log.info("Pressione Ctrl+C para parar.")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        log.info("Scheduler encerrado.")
        scheduler.shutdown()


if __name__ == "__main__":
    main()