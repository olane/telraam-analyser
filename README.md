# Telraam Traffic Explorer

Compare traffic data from [Telraam](https://telraam.net/) across calendar-aware
periods — holidays vs term time, the same holiday across years, or before/after
an intervention.

Telraam's built-in dashboard is great for day-to-day monitoring but doesn't let
you define arbitrary periods, align them by weekday, or look at long-term
trends. This app fills that gap.

## Features

- **Pick a sensor and a time range, then explore** — the sidebar downloads the
  whole selected range into the local parquet cache (rate limits excepted)
  independently of how you analyse it. A comparison recipe only labels periods
  in the already-loaded data.
- **Typed, calendar-aware periods** — school terms and holidays (Christmas,
  half terms, Easter, ...) are first-class, each tagged with a kind and an
  academic year so "similar periods" can be compared automatically.
- **Opinionated comparisons**
  - Holidays vs term time
  - Year on year (same holiday, different years)
  - Compare holiday types
  - Before / after an intervention, optionally with the same window last year
  - Custom selection of any periods
- **Weekday alignment** — like weekdays are compared with like, with an
  optional week-by-week breakdown for long holidays.
- **Trends over time** — daily totals with a rolling average, a
  weekday-adjusted trend, and a typical-week heatmap. Periods are shaded as
  bands on the timeline.
- **Exclusions** — drop roadworks, closures or other anomalies from analysis;
  excluded ranges are shown on the trend chart.
- **Speed, modal split and hourly profiles**, plus CSV export of derived
  aggregates.
- **Local parquet cache** with gap-filling, so each date range is fetched once.

## Setup

1. Create a virtual environment and install (Python **3.9+** is supported;
   3.10+ recommended):

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

   On macOS the system `python3` can be old (e.g. 3.9.6). If
   `python3 --version` is below 3.9, use a newer interpreter, e.g.
   `python3.12 -m venv .venv`.

2. Provide credentials. Either copy `.env.example` to `.env`:

   ```
   TELRAAM_API_KEY=your_api_key_here
   TELRAAM_SEGMENT_IDS=12345,67890
   ```

   or create `.streamlit/secrets.toml` with the same keys (recommended for a
   hosted deployment).

   You need a [Telraam API subscription](https://telraam.net/api/data-subscription)
   with advanced access, and your segment ID(s). Only the segment IDs listed
   here can be queried (unless `TELRAAM_ALLOW_ALL_SEGMENTS=true`).

3. Run:

   ```bash
   streamlit run app.py
   ```

## Running with Docker

The app ships with a `Dockerfile`, so it can run without a local Python install:

```bash
docker build -t telraam-analyser .

docker run -d --name telraam-analyser \
  --env-file .env \
  -v telraam-data:/data \
  -p 8501:8501 \
  telraam-analyser
```

Then open <http://localhost:8501>.

The image runs as a non-root user and stores its parquet cache (and the
file-backed request budget) under `/data`:

| Env var | Default (in image) | Purpose |
| --- | --- | --- |
| `TELRAAM_API_KEY` | — | Telraam API key (required) |
| `TELRAAM_SEGMENT_IDS` | — | Comma-separated segment allowlist (required) |
| `TELRAAM_CACHE_DIR` | `/data/cache` | Parquet cache + `.budget.json` location |
| `TELRAAM_DAILY_BUDGET` | `900` | Max upstream requests per day |
| `TELRAAM_ALLOW_ALL_SEGMENTS` | `false` | Allow querying any segment ID |

Mount a volume at `/data` to persist the cache across container restarts.
Prebuilt images are published to `ghcr.io/olane/telraam-analyser`.

## Calendars

Academic calendars live in `domain/calendars.py`. The Cambridge 2025-26 and
2026-27 years are populated. Add a year by copying an existing block in
`CAMBRIDGE_YEARS` and changing the dates — year-on-year comparisons then work
automatically.

Source for Cambridge term dates:
<https://www.cambridgeshire.gov.uk/residents/children-and-families/schools-learning/school-term-dates-closures>

## Tests

```bash
pytest
```

The suite covers the pure domain/analysis layer, structural checks on the
Plotly figures, plus a smoke test that renders every view with synthetic data
(no network required).

## Preview images

Many agent containers have no browser, so real screenshots aren't always
possible. `scripts/render_previews.py` draws representative images of the four
views with matplotlib using the **same** analysis functions the app uses. It
runs on synthetic data and needs no API key:

```bash
pip install -e ".[dev]"
python scripts/render_previews.py            # writes docs/screenshots/
python scripts/render_previews.py --out /tmp/pv --dpi 110
```

Reference the generated PNGs from a PR with raw GitHub URLs, e.g.
`https://raw.githubusercontent.com/<owner>/<repo>/<branch>/docs/screenshots/02_trends.png`.

## Architecture

```
UI (app.py + ui/ + views/)
        |
Analysis (analysis/) + Charts (charts/)
        |
Domain (domain/ — models + calendars)
        |
Data access (api_client.py + cache.py) → Telraam REST API + parquet cache
```

- `domain/` — typed periods, calendars, comparison configuration.
- `analysis/` — pure functions (DataFrame in, DataFrame out): filters,
  aggregates, weekday alignment, trends, comparison recipes.
- `charts/` — Plotly figure builders.
- `ui/` — theme, session state, sidebar controls, reusable components.
- `views/` — one module per page (Overview, Trends, Compare, Detail).
- Data layer — never called directly from views.

## Hosting notes

Because a hosted deployment can share one API key, the app includes:

- a segment **allowlist** (`TELRAAM_SEGMENT_IDS`),
- a persistent shared parquet cache,
- per-key **fetch coalescing** so concurrent visitors cause one upstream fetch,
- a file-backed **daily request budget** (`TELRAAM_DAILY_BUDGET`, default 900).

## Licence and attribution

Telraam data is licensed
[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) — free to use,
adapt and publish for **non-commercial** purposes with attribution. Commercial
reuse requires a separate agreement with Telraam (`info@telraam.net`). The app
shows an attribution footer and only exports derived aggregates, not raw data.
