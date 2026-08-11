# Bridging What Futures Miss

**Factor-Conditioned Moment-Matched Bridges for Commodity Portfolio Value at Risk**

This repository contains the public research materials for a method that
constructs missing commodity cash-month scenarios while retaining empirical
futures-factor history, calibrated linear dependence, finite-sample residual
moments, and observed cash-price endpoints.

The objective is not simply to increase Value at Risk. It is to represent the
location, delivery-block, prompt-period, and cross-market dependence omitted by
a futures-only historical simulation in a mathematically controlled way.

## Paper

The current paper is available as:

- [Bridging What Futures Miss](Bridging_What_Futures_Miss_Research_Paper.pdf)
- [Editable manuscript](Cash_VaR_Bridge_Research_Paper.md)
- [Bibliography](Cash_VaR_Bridge_Research_Paper.bib)

Author: Felix Kwok

With thanks to Shichang Liu and Christian Vargas for discussion and practical
insight into commodity cash-market risk. All remaining errors and
interpretations are the author's own.

## Repository Contents

```text
.
|-- README.md
|-- NOTICE.md
|-- CITATION.cff
|-- requirements.txt
|-- Cash_VaR_Bridge_Research_Paper.md
|-- Cash_VaR_Bridge_Research_Paper.bib
|-- Bridging_What_Futures_Miss_Research_Paper.pdf
|-- build_research_paper_pdf.py
`-- research_paper_figures/
    |-- exception_rates.png
    |-- gas_structural_fidelity.png
    |-- power_psd_adjustment.png
    |-- quantile_loss.png
    `-- storm_fern_loss_to_var.png
```

Operational bridge code, source-system connectors, proprietary mappings,
credentials, licensed observations, caches, internal database identifiers, and
firm-specific handoff documentation are deliberately excluded.

## Data Availability

The empirical study uses licensed daily physical gas assessments, licensed
hourly day-ahead and real-time power observations, and historical monthly
contract settlements. Those source observations cannot be redistributed in
this repository.

The manuscript and committed figures contain aggregate research results. An
external replication must source equivalent observations and independently
implement the vendor-neutral methodology described in the paper. The synthetic
appendix permits verification of the central algebra without licensed data.

Optional aggregate result files can be placed locally under `derived_results/`
to regenerate the figures. That directory is ignored and must not be committed
without an independent data-licensing review. The builder recognizes:

- `backtest_summary.csv`
- `storm_fern_summary.csv`
- `bridge_diagnostics.csv`
- `gas_structural_fidelity.csv`

When those files are absent, the committed figures are used unchanged.

## Rebuilding the PDF

The document builder requires Python, Pandoc, and Tectonic. Create an
environment and install the Python dependencies:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Place `pandoc` and `tectonic` on `PATH`, set `PANDOC_PATH` and `TECTONIC_PATH`
to their executable files, or install them beneath `.tools/pandoc` and
`.tools/tectonic`. Then run:

```powershell
.\.venv\Scripts\python.exe .\build_research_paper_pdf.py
```

Temporary TeX and compilation files are written under the ignored `.build/`
directory. The compiled PDF is written to the repository root.

## Research Scope

The paper evaluates one-day 95 percent historical VaR for normalized delta-one
gas and power portfolios. It compares futures-only scenarios, independently
paired basis scenarios, rolling cash proxies, and the proposed bridge. The
construction controls first and second moments and linear dependence; it does
not claim to preserve the complete higher-order residual distribution or to
eliminate severe stress losses.

The results are research evidence, not production certification. External use
requires independent model validation, point-in-time data controls, appropriate
tail and stress testing, and governance for the intended portfolio.

## Citation

Repository citation metadata is provided in [CITATION.cff](CITATION.cff). Until
a journal citation or DOI is available, cite the manuscript as:

```text
Kwok, Felix. "Bridging What Futures Miss: Factor-Conditioned Moment-Matched
Bridges for Commodity Portfolio Value at Risk." Working paper, August 2026.
```

## Rights and Disclaimer

See [NOTICE.md](NOTICE.md). No underlying market data is included or licensed
for redistribution. The material is provided for research discussion and is not
investment advice or a production risk limit.
