# MLB Lab · Vision with Data
A free Sports Labs product: proprietary **Home Run Score** (P(1+ HR) per batter-game, 1-99) and **Strikeout King of the Day** (starter K projections with fatigue/workload model), walk-forward backtested on the 2026 regular season.

Live: https://mkuritz.github.io/mlb-lab/

- Sources ($0): MLB Stats API, Baseball Savant/Statcast (pybaseball), Open-Meteo, Kalshi public markets, DraftKings props via Bet Lab's credit-guarded Odds API pull (`bet-lab/data/mlb_dk_props.json`). No RotoWire/RotoWorld/FanGraphs scraping.
- Exports for Bet Lab: `data/hr_scores.json`, `data/k_projections.json`.
- Backtests: `scripts/backtest_hr.py`, `scripts/backtest_k.py` -> `data/backtest_*.json`; fatigue case study `scripts/fatigue.py` -> `data/fatigue_case.json`.
- Refresh: `.github/workflows/update.yml` runs `scripts/build.py` (daily + pre-game).

MLB Lab · A Sports Labs Product · Property of Michael Kuritz
