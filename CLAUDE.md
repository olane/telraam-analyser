# Telraam Traffic Explorer

## Project overview
Streamlit app that fetches traffic data from the Telraam API and lets users
compare calendar-aware periods (school holidays vs term time, the same holiday
across years, before/after an intervention). Periods are typed (kind +
academic year), aligned by weekday, and can be shown as long-term trends with
exclusions (e.g. roadworks) shaded out.

## Architecture
```
UI (app.py + ui/ + views/) → Analysis (analysis/) + Charts (charts/) → Domain (domain/) → Data (api_client.py + cache.py) → Telraam REST API
```
- `domain/` is pure data: `models.py` (PeriodKind, PeriodInstance, Calendar,
  Exclusion, ComparisonConfig) and `calendars.py` (data-driven academic years).
- `analysis/` is pure: DataFrame in, DataFrame out, no I/O. Split into
  `filters`, `aggregates`, `align` (weekday), `trends`, `comparisons`.
- `charts/` builds Plotly figures with a shared `theme.py`.
- `ui/` holds theme/CSS, session state (`state.py`), sidebar (`controls.py`) and
  reusable components. `views/` holds one `render()` per page.
- Views never call the API directly.

## Running
```
pip install -e ".[dev]"
streamlit run app.py
pytest
```
Requires `TELRAAM_API_KEY` and `TELRAAM_SEGMENT_IDS` — from `.env` locally or
`.streamlit/secrets.toml` when hosted (secrets take precedence).

## Key conventions
- Use `python3` not `python` (macOS Homebrew)
- Parquet cache lives in `data/` (gitignored), one file per (segment_id, level,
  format); the cache manager fills gaps and coalesces concurrent fetches
- `analysis.py`/`charts.py` logic is split into packages; keep `analysis/` pure
- Periods are first-class: a `PeriodInstance` has a `PeriodKind`, ranges and an
  `academic_year`; `Calendar` groups them
- Default comparison alignment is weekday (`Alignment.WEEKDAY`)
- Add academic years in `domain/calendars.py::CAMBRIDGE_YEARS`; year-on-year
  works automatically once a second year exists
- API requests are chunked at 90-day boundaries with 1 req/sec rate limiting; a
  daily request budget guards a public deployment
- Modalities: pedestrian, bike, car, heavy, night (+ _lft/_rgt variants for S2)
- Telraam data is CC BY-NC 4.0 — keep the attribution footer, no commercial use,
  aggregate-only exports
- No browser in most agent containers: use `scripts/render_previews.py` to render
  synthetic-data previews into `docs/screenshots/` instead of screenshots
