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
- Download is decoupled from analysis: the sidebar picks a sensor + time range
  and fetches the whole range (cache-filled, budget-guarded); a comparison axis
  (`ComparisonMode`) then only groups the already-loaded data (via
  `group_label`) and is shared by every view — never one bucket per period
- Comparison aggregations/charts take a `group_col` (default `period_label`),
  so the pure API stays backward compatible while views pass `group_label`
- `analysis/pipeline.py::prepare_frame` is the pure frame-prep shared by views
- Add academic years in `domain/calendars.py::CAMBRIDGE_YEARS`; year-on-year
  works automatically once a second year exists
- API requests are chunked at 90-day boundaries with 1 req/sec rate limiting; a
  daily request budget guards a public deployment
- Modalities: pedestrian, bike, car, heavy, night (+ _lft/_rgt variants for S2);
  `motorised` is a derived group = car + heavy + night×`NIGHT_MOTORISED_SHARE`
  (night is headlight-only, so that share scales out the estimated bike portion;
  0.8 for now, can be derived from daytime shares). Groups are offered in
  per-view sub-filters (e.g. the Trends "Trend modality" picker), not the sidebar
- Telraam data is CC BY-NC 4.0 — keep the attribution footer, no commercial use,
  aggregate-only exports
- No browser in most agent containers: use `scripts/render_previews.py` to render
  synthetic-data previews into `docs/screenshots/` instead of screenshots

## Deployment
- `Dockerfile` builds a non-root Streamlit image; `CMD` serves on `0.0.0.0:8501`
- Published to GHCR as `ghcr.io/olane/telraam-analyser` by
  `.github/workflows/publish.yml` on pushes to `main`
- Consumed by the homelab stack (`olane/pod-internal-docker`) behind Caddy at
  `telraam.olane.dev` (LAN-only)
- Cache path is env-configurable via `TELRAAM_CACHE_DIR` (default `data`); the
  image points it at `/data/cache`, so a single `/data` volume persists the
  parquet cache and the file-backed request budget
