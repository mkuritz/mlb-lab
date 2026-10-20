# MLB Lab · Vision with Data
A free Sports Labs product: proprietary **Home Run Score** (P(1+ HR) per batter-game, 1-99) and **Strikeout King of the Day** (starter K projections with fatigue/workload model), walk-forward backtested on the 2026 regular season.

Live: https://mlblab.sportslabshq.com/

- Sources ($0): official league data, public Statcast data, weather forecasts, public exchange and book prices.
- Exports for Bet Lab: `data/hr_scores.json`, `data/k_projections.json`.
- Backtests: `scripts/backtest_hr.py`, `scripts/backtest_k.py` -> `data/backtest_*.json`; fatigue case study `scripts/fatigue.py` -> `data/fatigue_case.json`.
- Refresh: `.github/workflows/update.yml` runs `scripts/build.py` (daily + pre-game).

MLB Lab · A Sports Labs Product · Property of Michael Kuritz


## How this repo is built
The Home Run Score and Strikeout King models (code, weights, features, full outputs) live in a **private** engine repo.
Its GitHub Action builds the slate and pushes **display-ready fields only** into `data/` here. Nothing in this repo
is enough to reproduce the models. Note: model scripts and feature caches that were in this repo before Oct 15, 2026
remain in git history.

Data: official league data, public Statcast data, weather forecasts, public exchange prices. News & roundups are written by
Sports Labs from official MLB box scores and transactions.

MLB Lab · A Sports Labs Product
