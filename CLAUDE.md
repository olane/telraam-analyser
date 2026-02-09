# Telraam Traffic Comparison App

## Project overview
Streamlit multi-page app that fetches traffic data from the Telraam API and lets users compare custom time periods (e.g. school holidays vs term time). Users define named "period groups" with multiple date ranges, apply time-of-day and day-of-week filters, and view comparative charts.

## Architecture
```
UI (app.py + pages/) → Analysis (analysis.py) + Charts (charts.py) → Data (api_client.py + cache.py) → Telraam REST API
```
Each layer only talks to the one below it. Pages never call the API directly.

## Running
```
pip install -e .
streamlit run app.py
```
Requires `.env` with `TELRAAM_API_KEY` and `TELRAAM_SEGMENT_IDS`.

## Key conventions
- Use `python3` not `python` (macOS Homebrew)
- Parquet cache lives in `data/` (gitignored), one file per (segment_id, level, format)
- `analysis.py` functions are pure — DataFrame in, DataFrame out, no I/O
- Period groups are first-class: a named group contains multiple disjoint date ranges
- API requests are auto-chunked at 90-day boundaries with 1-second rate limiting
- Modalities: pedestrian, bike, car, heavy (+ _lft/_rgt variants for S2 sensors)
