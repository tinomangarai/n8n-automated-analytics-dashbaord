"""
Alpha Vintage Analytics — Single entry point.

Usage:
  python run_pipeline.py                 # Run full pipeline (fetch + analyse + report)
  python run_pipeline.py --fetch         # Fetch & cache raw data only
  python run_pipeline.py --analyse       # Analyse already-cached data
  python run_pipeline.py --report        # Generate PDF report (requires cached data)
  python run_pipeline.py --dashboard     # Launch Streamlit dashboard
  python run_pipeline.py --symbols MSFT AAPL   # Override symbols for this run
  python run_pipeline.py --output-dir /path    # Override report output directory
"""
import sys
import os
import argparse
import subprocess
from pathlib import Path

# Detect whether we have a real terminal before importing rich
_IS_TTY = sys.stdout.isatty()
if not _IS_TTY:
    os.environ["NO_COLOR"] = "1"

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import track as _rich_track
from loguru import logger

# Ensure project root is importable from any launch location
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import SYMBOLS, REPORTS_DIR, COMPANY_NAME
from config.logging_config import setup_logging

setup_logging()
# Headless mode (subprocess): plain output, no Windows console API
console = Console(force_terminal=_IS_TTY, no_color=not _IS_TTY)

def track(iterable, description=""):
    """Drop-in for rich.progress.track — plain iterator when no TTY."""
    if _IS_TTY:
        yield from _rich_track(iterable, description=description)
    else:
        yield from iterable


# ── Helpers ───────────────────────────────────────────────────────────────────

def banner() -> None:
    console.print(Panel(
        f"[bold cyan]{COMPANY_NAME}[/bold cyan]\n"
        "[dim]Alpha Vantage  ·  DuckDB  ·  Streamlit  ·  Plotly  ·  ReportLab[/dim]",
        title="Financial Analytics Pipeline",
        border_style="cyan",
        expand=False,
    ))


def _load_and_enrich(symbols: list[str], use_cache: bool = True) -> dict:
    """Fetch, clean, and feature-engineer all symbols. Returns {symbol: DataFrame}."""
    from ingestion.alpha_vantage_client import fetch_daily_ohlcv, fetch_rsi
    from processing.data_cleaner import DataCleaner
    from processing.feature_engineer import engineer_features

    cleaner = DataCleaner()
    result = {}

    for sym in track(symbols, description="Loading symbols..."):
        try:
            raw = fetch_daily_ohlcv(sym, use_cache=use_cache)
            clean = cleaner.clean_ohlcv(raw, sym)

            import pandas as _pd
            rsi_df = None
            try:
                rsi_df = fetch_rsi(sym)
            except Exception as e:
                logger.warning(f"RSI fetch failed for {sym}: {e}")

            merged = cleaner.align_and_merge(
                clean,
                rsi_df if rsi_df is not None else _pd.DataFrame(),
                _pd.DataFrame(),
                _pd.DataFrame(),
            )
            result[sym] = engineer_features(merged)
            console.print(f"  [green]OK[/green] {sym} - {len(result[sym])} rows loaded")

        except Exception as e:
            console.print(f"  [red]FAIL[/red] {sym} - {e}")
            logger.error(f"Failed to load {sym}: {e}")

    return result


def _print_summary(results: dict) -> None:
    """Print performance summary table to the terminal."""
    per_sym = results.get("per_symbol", {})
    tbl = Table(title="Performance Summary", header_style="bold cyan", show_lines=True)
    tbl.add_column("Symbol", style="bold")
    tbl.add_column("Price",       justify="right")
    tbl.add_column("Total Return",justify="right")
    tbl.add_column("CAGR",        justify="right")
    tbl.add_column("Volatility",  justify="right")
    tbl.add_column("Sharpe",      justify="right")
    tbl.add_column("Max DD",      justify="right")
    tbl.add_column("Trend")

    for sym, data in per_sym.items():
        p = data.get("performance", {})
        s = data.get("summary", {})
        t = data.get("trends", {})
        tbl.add_row(
            sym,
            f"${s.get('current_price', 0):,.2f}",
            f"[{'green' if s.get('total_return_pct',0)>=0 else 'red'}]{s.get('total_return_pct', 0):+.1f}%[/]",
            f"[{'green' if p.get('cagr_pct',0)>=0 else 'red'}]{p.get('cagr_pct', 0):+.1f}%[/]",
            f"{p.get('annualised_volatility_pct', 0):.1f}%",
            f"{p.get('sharpe_ratio', 0):.2f}",
            f"{p.get('max_drawdown_pct', 0):.1f}%",
            t.get("trend_class", "N/A"),
        )
    console.print(tbl)


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_fetch(symbols: list[str]) -> dict:
    console.print(f"\n[bold cyan]Fetching data for: {', '.join(symbols)}[/bold cyan]")
    data = _load_and_enrich(symbols, use_cache=False)
    console.print(f"[green]OK Fetched {len(data)} symbol(s)[/green]")
    return data


def cmd_analyse(symbols: list[str], symbol_data: dict | None = None) -> tuple[dict, dict]:
    if symbol_data is None:
        console.print("\n[bold cyan]Loading cached data...[/bold cyan]")
        symbol_data = _load_and_enrich(symbols, use_cache=True)

    console.print("\n[bold cyan]Running analysis engine...[/bold cyan]")
    from analysis.analyzer import MarketAnalyzer
    analyzer = MarketAnalyzer(symbol_data)
    results  = analyzer.run()
    _print_summary(results)

    console.print("\n[bold green]Insights:[/bold green]")
    for i, insight in enumerate(results.get("insights", []), 1):
        console.print(f"  {i}. {insight}")

    return symbol_data, results


def cmd_report(symbol_data: dict, results: dict, output_dir: str | None = None) -> str:
    console.print("\n[bold cyan]Generating PDF report...[/bold cyan]")
    from reporting.pdf_reporter import PDFReporter
    import os

    reporter = PDFReporter()
    if output_dir:
        from datetime import datetime
        path = str(Path(output_dir) / f"market_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        pdf_path = reporter.generate(symbol_data, results, output_path=path)
    else:
        pdf_path = reporter.generate(symbol_data, results)

    console.print(f"[green]OK Report saved:[/green] {pdf_path}")
    return pdf_path


def cmd_dashboard() -> None:
    console.print("\n[bold cyan]Launching Streamlit dashboard...[/bold cyan]")
    console.print("[dim]Open http://localhost:8501 in your browser[/dim]")
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(Path(__file__).parent / "dashboard" / "app.py"),
        "--server.port", "8501",
        "--server.headless", "false",
        "--browser.gatherUsageStats", "false",
    ])


def cmd_full(symbols: list[str], output_dir: str | None = None) -> None:
    console.print("[bold]Running FULL pipeline...[/bold]")
    symbol_data = cmd_fetch(symbols)
    symbol_data, results = cmd_analyse(symbols, symbol_data)
    pdf_path = cmd_report(symbol_data, results, output_dir=output_dir)
    console.print(Panel(
        f"[bold green]Pipeline complete![/bold green]\n"
        f"PDF: {pdf_path}\n\n"
        f"Launch dashboard with:\n  [cyan]python run_pipeline.py --dashboard[/cyan]",
        border_style="green",
    ))


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Alpha Vintage Financial Analytics Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--fetch",      action="store_true", help="Fetch raw data only")
    parser.add_argument("--analyse",    action="store_true", help="Analyse cached data")
    parser.add_argument("--report",     action="store_true", help="Generate PDF report")
    parser.add_argument("--dashboard",  action="store_true", help="Launch dashboard")
    parser.add_argument("--symbols",    nargs="+", default=SYMBOLS, help="Override symbols")
    parser.add_argument("--output-dir", default=None, help="Override report output directory")
    parser.add_argument("--no-cache",   action="store_true", help="Force fresh API fetch")

    args = parser.parse_args()
    banner()

    symbols = [s.upper() for s in args.symbols]

    if args.dashboard:
        cmd_dashboard()
    elif args.fetch:
        cmd_fetch(symbols)
    elif args.analyse:
        cmd_analyse(symbols)
    elif args.report:
        symbol_data, results = cmd_analyse(symbols)
        cmd_report(symbol_data, results, output_dir=args.output_dir)
    else:
        # Default: full pipeline
        cmd_full(symbols, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
