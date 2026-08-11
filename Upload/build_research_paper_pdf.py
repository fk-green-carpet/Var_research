"""Build the external cash-VaR research paper as a LaTeX PDF.

Optional aggregate result files under ``derived_results`` are used to regenerate
the paper's figures when available. Existing committed figures remain sufficient
to compile the paper without redistributing licensed source observations.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent
SOURCE_PATH = PROJECT_DIR / "Cash_VaR_Bridge_Research_Paper.md"
BIBLIOGRAPHY_PATH = PROJECT_DIR / "Cash_VaR_Bridge_Research_Paper.bib"
OUTPUT_PATH = PROJECT_DIR / "Bridging_What_Futures_Miss_Research_Paper.pdf"
FIGURE_DIR = PROJECT_DIR / "research_paper_figures"

DATA_DIR = PROJECT_DIR / "derived_results"
SUMMARY_PATH = DATA_DIR / "backtest_summary.csv"
FERN_SUMMARY_PATH = DATA_DIR / "storm_fern_summary.csv"
DIAGNOSTICS_PATH = DATA_DIR / "bridge_diagnostics.csv"
STRUCTURAL_FIDELITY_PATH = DATA_DIR / "gas_structural_fidelity.csv"

BUILD_DIR = PROJECT_DIR / ".build"
HEADER_PATH = BUILD_DIR / "research_paper_header.tex"
TEX_PATH = BUILD_DIR / "Bridging_What_Futures_Miss_Research_Paper.tex"

PANDOC_ROOT = PROJECT_DIR / ".tools" / "pandoc"
TECTONIC_ROOT = PROJECT_DIR / ".tools" / "tectonic"

FIGURE_PATHS = {
    "gas_structure": FIGURE_DIR / "gas_structural_fidelity.png",
    "exception_rates": FIGURE_DIR / "exception_rates.png",
    "quantile_loss": FIGURE_DIR / "quantile_loss.png",
    "fern": FIGURE_DIR / "storm_fern_loss_to_var.png",
    "psd": FIGURE_DIR / "power_psd_adjustment.png",
}

METHOD_ORDER = [
    "futures_only",
    "independent_basis",
    "rolling_cash",
    "bridge",
]
METHOD_LABELS = {
    "futures_only": "Futures only",
    "independent_basis": "Independent basis",
    "rolling_cash": "Rolling cash",
    "bridge": "Bridge",
}
METHOD_COLORS = {
    "futures_only": "#6B6F73",
    "independent_basis": "#B45F35",
    "rolling_cash": "#3D7A5E",
    "bridge": "#2F5D8A",
}
METHOD_HATCHES = {
    "futures_only": "",
    "independent_basis": "//",
    "rolling_cash": "..",
    "bridge": "xx",
}
PORTFOLIO_LABELS = {
    "Gas: Algonquin Citygate": "Algonquin",
    "Gas: concentrated Northeast": "Northeast",
    "Gas: diversified regional": "Diversified",
    "Power: PJM West RT peak": "PJM West\nRT peak",
    "Power: concentrated PJM": "Concentrated\nPJM",
    "Power: diversified regional": "Diversified",
}
PORTFOLIO_ORDER = {
    "Gas": [
        "Gas: Algonquin Citygate",
        "Gas: concentrated Northeast",
        "Gas: diversified regional",
    ],
    "Power": [
        "Power: PJM West RT peak",
        "Power: concentrated PJM",
        "Power: diversified regional",
    ],
}

LONGTABLE_PATTERN = re.compile(r"\\begin\{longtable\}\[\]\{@\{\}([lrc]+)@\{\}\}")
INLINE_CODE_PATTERN = re.compile(
    r"\\passthrough\{\\lstinline!(.*?)!\}",
    flags=re.DOTALL,
)

LATEX_HEADER = r"""
\usepackage{microtype}
\usepackage{setspace}
\usepackage{enumitem}
\usepackage{xurl}
\usepackage{etoolbox}
\usepackage{amsthm}
\usepackage{float}
\usepackage{caption}

\setstretch{1.035}
\setlength{\parindent}{1.25em}
\setlength{\parskip}{0.05\baselineskip}
\setlength{\emergencystretch}{2.5em}
\setlength{\LTpre}{0.45\baselineskip}
\setlength{\LTpost}{0.65\baselineskip}
\renewcommand{\arraystretch}{1.08}
\setlist{nosep,leftmargin=1.75em,topsep=0.3\baselineskip}
\captionsetup{font=small,labelfont=bf,labelsep=period}
\AtBeginEnvironment{longtable}{\footnotesize\setlength{\tabcolsep}{3.5pt}}
\AtBeginEnvironment{quote}{\small}
\newtheorem{proposition}{Proposition}

\lstset{
  basicstyle=\ttfamily\scriptsize,
  breaklines=true,
  breakatwhitespace=false,
  columns=fullflexible,
  keepspaces=true,
  frame=single,
  framerule=0.25pt,
  rulecolor=\color{black!45},
  showstringspaces=false,
  tabsize=4,
  xleftmargin=0.5em,
  xrightmargin=0.5em,
  aboveskip=0.55\baselineskip,
  belowskip=0.65\baselineskip
}
""".strip()


def find_tool(name: str, search_root: Path) -> Path:
    configured = os.getenv(f"{name.upper()}_PATH")
    if configured:
        configured_path = Path(configured).expanduser().resolve()
        if configured_path.is_file():
            return configured_path
        raise FileNotFoundError(
            f"{name.upper()}_PATH does not identify a file: {configured_path}"
        )
    executable = shutil.which(name)
    if executable:
        return Path(executable)
    candidates = (
        sorted(search_root.rglob(f"{name}.exe"), reverse=True)
        if search_root.exists()
        else []
    )
    if candidates:
        return candidates[0]
    raise FileNotFoundError(
        f"{name} was not found. Put it on PATH, set {name.upper()}_PATH, "
        f"or install it under {search_root}."
    )


def run_checked(command: list[str], *, cwd: Path, timeout: int) -> None:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Command failed ({completed.returncode}): "
            f"{subprocess.list2cmdline(command)}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )


def configure_plot_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.size": 8.5,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": "#303030",
            "axes.linewidth": 0.7,
            "grid.color": "#D8D8D8",
            "grid.linewidth": 0.5,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def method_bars(
    ax: plt.Axes,
    frame: pd.DataFrame,
    portfolios: list[str],
    value_column: str,
) -> None:
    x = np.arange(len(portfolios), dtype=float)
    width = 0.19
    offsets = (np.arange(len(METHOD_ORDER)) - 1.5) * width
    for offset, method in zip(offsets, METHOD_ORDER, strict=True):
        selected = frame.loc[frame["method"].eq(method)].set_index("portfolio")
        values = selected.reindex(portfolios)[value_column].to_numpy(dtype=float)
        ax.bar(
            x + offset,
            values,
            width=width,
            label=METHOD_LABELS[method],
            color=METHOD_COLORS[method],
            edgecolor="#222222",
            linewidth=0.35,
            hatch=METHOD_HATCHES[method],
            zorder=3,
        )
    ax.set_xticks(x, [PORTFOLIO_LABELS[name] for name in portfolios])
    ax.grid(axis="y", zorder=0)


def save_figure(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=260, bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)


def plot_exception_rates(summary: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(7.25, 3.0))
    for ax, commodity in zip(axes, ["Gas", "Power"], strict=True):
        selected = summary.loc[summary["commodity"].eq(commodity)].copy()
        selected["exception_percent"] = 100.0 * selected["exception_rate"]
        method_bars(
            ax,
            selected,
            PORTFOLIO_ORDER[commodity],
            "exception_percent",
        )
        ax.axhline(5.0, color="#111111", linestyle="--", linewidth=1.0, zorder=4)
        ax.set_title(commodity)
        ax.set_ylim(0.0, 48.0)
        ax.set_ylabel("Exception rate (%)" if commodity == "Gas" else "")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.84))
    save_figure(fig, FIGURE_PATHS["exception_rates"])


def plot_quantile_loss(summary: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(7.25, 3.0))
    for ax, commodity in zip(axes, ["Gas", "Power"], strict=True):
        selected = summary.loc[summary["commodity"].eq(commodity)]
        method_bars(
            ax,
            selected,
            PORTFOLIO_ORDER[commodity],
            "mean_quantile_loss",
        )
        ax.set_title(commodity)
        ax.set_ylabel("Mean quantile loss" if commodity == "Gas" else "")
        ax.set_ylim(bottom=0.0)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.84))
    save_figure(fig, FIGURE_PATHS["quantile_loss"])


def plot_gas_structural_fidelity(structural: pd.DataFrame) -> None:
    gas = structural.loc[structural["commodity"].eq("Gas")].copy()
    metric_specs = [
        ("factor_loading_rmse", "Mapped-factor loading"),
        ("cash_correlation_rmse", "Cash correlation"),
        ("residual_correlation_rmse", "Residual correlation"),
    ]
    short_labels = {
        "futures_only": "Futures\nonly",
        "independent_basis": "Indep.\nbasis",
        "rolling_cash": "Rolling\ncash",
        "bridge": "Bridge",
    }
    fig, axes = plt.subplots(1, 3, figsize=(7.25, 2.95), constrained_layout=True)
    for ax, (metric, title) in zip(axes, metric_specs, strict=True):
        data: list[np.ndarray] = []
        positions: list[int] = []
        methods: list[str] = []
        for position, method in enumerate(METHOD_ORDER, start=1):
            values = pd.to_numeric(
                gas.loc[gas["method"].eq(method), metric],
                errors="coerce",
            ).dropna()
            if values.empty:
                continue
            data.append(np.maximum(values.to_numpy(dtype=float), 1e-16))
            positions.append(position)
            methods.append(method)
        boxes = ax.boxplot(
            data,
            positions=positions,
            widths=0.62,
            whis=(5, 95),
            showfliers=False,
            patch_artist=True,
            medianprops={"color": "#111111", "linewidth": 1.0},
            boxprops={"edgecolor": "#222222", "linewidth": 0.55},
            whiskerprops={"color": "#444444", "linewidth": 0.65},
            capprops={"color": "#444444", "linewidth": 0.65},
        )
        for patch, method in zip(boxes["boxes"], methods, strict=True):
            patch.set_facecolor(METHOD_COLORS[method])
            patch.set_hatch(METHOD_HATCHES[method])
        ax.set_yscale("log")
        ax.set_xlim(0.5, 4.5)
        ax.set_xticks(
            range(1, 5),
            [short_labels[method] for method in METHOD_ORDER],
        )
        ax.set_title(title)
        ax.grid(axis="y", which="major", zorder=0)
        if metric == "residual_correlation_rmse":
            lower = ax.get_ylim()[0]
            ax.text(
                1.0,
                lower * 1.35,
                "No residual",
                ha="center",
                va="bottom",
                fontsize=7,
                color="#555555",
            )
    axes[0].set_ylabel("Monthly structural RMSE (log scale)")
    save_figure(fig, FIGURE_PATHS["gas_structure"])


def plot_fern(fern: pd.DataFrame) -> None:
    portfolios = PORTFOLIO_ORDER["Gas"] + PORTFOLIO_ORDER["Power"]
    labels = [
        "Gas\nAlgonquin",
        "Gas\nNortheast",
        "Gas\nDiversified",
        "Power\nWest RT peak",
        "Power\nConcentrated",
        "Power\nDiversified",
    ]
    fig, ax = plt.subplots(figsize=(7.25, 3.35), constrained_layout=True)
    x = np.arange(len(portfolios), dtype=float)
    width = 0.19
    offsets = (np.arange(len(METHOD_ORDER)) - 1.5) * width
    for offset, method in zip(offsets, METHOD_ORDER, strict=True):
        selected = fern.loc[fern["method"].eq(method)].set_index("portfolio")
        values = selected.reindex(portfolios)["worst_loss_to_var"].to_numpy(dtype=float)
        ax.bar(
            x + offset,
            values,
            width=width,
            label=METHOD_LABELS[method],
            color=METHOD_COLORS[method],
            edgecolor="#222222",
            linewidth=0.35,
            hatch=METHOD_HATCHES[method],
            zorder=3,
        )
    ax.set_yscale("log")
    ax.axhline(1.0, color="#111111", linestyle="--", linewidth=1.0, zorder=4)
    ax.set_ylabel("Worst loss / forecast VaR (log scale)")
    ax.set_xticks(x, labels)
    ax.set_ylim(1.0, 600.0)
    ax.grid(axis="y", which="both", zorder=0)
    ax.legend(loc="upper center", ncol=4, frameon=False)
    save_figure(fig, FIGURE_PATHS["fern"])


def plot_psd_adjustment(diagnostics: pd.DataFrame) -> None:
    power = diagnostics.loc[diagnostics["commodity"].eq("Power")].copy()
    power["position_month"] = pd.to_datetime(power["position_month"])
    power = power.sort_values("position_month")
    plotted = np.maximum(power["psd_adjustment"].to_numpy(dtype=float), 1e-16)

    fig, ax = plt.subplots(figsize=(7.0, 2.75), constrained_layout=True)
    ax.plot(
        power["position_month"],
        plotted,
        color=METHOD_COLORS["bridge"],
        linewidth=1.0,
        marker="o",
        markersize=2.3,
    )
    ax.axhline(0.01, color=METHOD_COLORS["independent_basis"], linestyle="--", linewidth=0.9)
    ax.set_yscale("log")
    ax.set_ylim(1e-16, 1.0)
    ax.set_ylabel("Maximum entrywise adjustment")
    ax.set_xlabel("Power position month")
    ax.grid(axis="y", which="major")
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    maximum = power.loc[power["psd_adjustment"].idxmax()]
    ax.annotate(
        f"{maximum['psd_adjustment']:.3f}\n{maximum['position_month']:%b %Y}",
        xy=(maximum["position_month"], maximum["psd_adjustment"]),
        xytext=(-52, -4),
        textcoords="offset points",
        arrowprops={"arrowstyle": "->", "color": "#333333", "linewidth": 0.7},
        ha="right",
        va="center",
        fontsize=8,
    )
    save_figure(fig, FIGURE_PATHS["psd"])


def generate_figures() -> None:
    data_paths = [SUMMARY_PATH, FERN_SUMMARY_PATH, DIAGNOSTICS_PATH]
    if not all(path.exists() for path in data_paths):
        missing_figures = [path for path in FIGURE_PATHS.values() if not path.exists()]
        if missing_figures:
            raise FileNotFoundError(
                "Aggregate result files are unavailable and these committed figures "
                f"are missing: {missing_figures}"
            )
        return

    summary = pd.read_csv(SUMMARY_PATH)
    fern = pd.read_csv(FERN_SUMMARY_PATH)
    diagnostics = pd.read_csv(DIAGNOSTICS_PATH)
    configure_plot_style()
    plot_exception_rates(summary)
    plot_quantile_loss(summary)
    plot_fern(fern)
    plot_psd_adjustment(diagnostics)
    if STRUCTURAL_FIDELITY_PATH.exists():
        plot_gas_structural_fidelity(pd.read_csv(STRUCTURAL_FIDELITY_PATH))
    elif not FIGURE_PATHS["gas_structure"].exists():
        raise FileNotFoundError(
            "Gas structural-fidelity data and the committed structural figure are missing."
        )


def constrain_longtables(tex_source: str) -> str:
    widths_by_count = {
        3: (0.22, 0.34, 0.34),
        4: (0.17, 0.22, 0.43, 0.10),
        6: (0.18, 0.12, 0.16, 0.11, 0.13, 0.13),
        7: (0.18, 0.17, 0.11, 0.11, 0.10, 0.11, 0.10),
    }

    def replace(match: re.Match[str]) -> str:
        alignments = match.group(1)
        widths = widths_by_count.get(len(alignments))
        if widths is None:
            available = 0.90 - 0.012 * (len(alignments) - 1)
            widths = tuple(available / len(alignments) for _ in alignments)
        columns: list[str] = []
        for alignment, width in zip(alignments, widths, strict=True):
            declaration = {
                "l": r">{\raggedright\arraybackslash}",
                "c": r">{\centering\arraybackslash}",
                "r": r">{\raggedleft\arraybackslash}",
            }[alignment]
            columns.append(f"{declaration}p{{{width:.3f}\\linewidth}}")
        return r"\begin{longtable}[]{@{}" + "".join(columns) + r"@{}}"

    return LONGTABLE_PATTERN.sub(replace, tex_source)


def make_inline_code_breakable(tex_source: str) -> str:
    def replace(match: re.Match[str]) -> str:
        code = match.group(1).replace(r"\_", "_").replace(r"\^", "^")
        return r"{\ttfamily\nolinkurl{" + code + "}}"

    return INLINE_CODE_PATTERN.sub(replace, tex_source)


def build_pdf() -> Path:
    for required in [SOURCE_PATH, BIBLIOGRAPHY_PATH]:
        if not required.exists():
            raise FileNotFoundError(f"Required paper source not found: {required}")

    generate_figures()
    pandoc = find_tool("pandoc", PANDOC_ROOT)
    tectonic = find_tool("tectonic", TECTONIC_ROOT)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    build_figure_dir = BUILD_DIR / FIGURE_DIR.name
    build_figure_dir.mkdir(parents=True, exist_ok=True)
    for figure_path in FIGURE_PATHS.values():
        shutil.copy2(figure_path, build_figure_dir / figure_path.name)
    HEADER_PATH.write_text(LATEX_HEADER + "\n", encoding="utf-8")

    pandoc_command = [
        str(pandoc),
        str(SOURCE_PATH),
        "--from=markdown+tex_math_dollars+raw_tex",
        "--to=latex",
        "--standalone",
        "--citeproc",
        "--number-sections",
        "--listings",
        "--wrap=none",
        "--variable=documentclass:article",
        "--variable=classoption:11pt",
        "--variable=papersize:letter",
        "--variable=geometry:margin=0.92in",
        f"--bibliography={BIBLIOGRAPHY_PATH}",
        f"--resource-path={PROJECT_DIR}",
        f"--include-in-header={HEADER_PATH}",
        f"--output={TEX_PATH}",
    ]
    run_checked(pandoc_command, cwd=PROJECT_DIR, timeout=240)

    tex_source = TEX_PATH.read_text(encoding="utf-8")
    tex_source = constrain_longtables(tex_source)
    tex_source = make_inline_code_breakable(tex_source)
    TEX_PATH.write_text(tex_source, encoding="utf-8")

    tectonic_command = [
        str(tectonic),
        "--keep-logs",
        "--keep-intermediates",
        "--reruns=3",
        f"--outdir={BUILD_DIR}",
        str(TEX_PATH),
    ]
    run_checked(tectonic_command, cwd=BUILD_DIR, timeout=900)

    compiled_pdf = BUILD_DIR / f"{TEX_PATH.stem}.pdf"
    if not compiled_pdf.exists() or compiled_pdf.stat().st_size < 20_000:
        raise RuntimeError(f"Tectonic did not create a valid PDF: {compiled_pdf}")
    shutil.copy2(compiled_pdf, OUTPUT_PATH)
    return OUTPUT_PATH


if __name__ == "__main__":
    output = build_pdf()
    print(f"Built {output} ({output.stat().st_size:,} bytes)")
