# Telraam Analyser

Compare traffic data from [Telraam](https://telraam.net/) across custom time periods — e.g. school holidays vs term time, or before vs after roadworks.

Telraam's built-in dashboard is great for day-to-day monitoring, but doesn't support defining arbitrary date ranges and comparing them side by side. This app fills that gap.

## Features

- **Custom period groups** — define named groups (e.g. "Term time", "School holidays") each containing multiple disjoint date ranges
- **Built-in presets** — Cambridge school term/holiday dates for 2025-26, with save/load for your own configurations
- **Flexible filtering** — filter by time of day, day of week, and transport modality
- **Four chart views:**
  - Hourly profile (average by hour of day)
  - Daily volume (time series of daily totals)
  - Modal split (percentage breakdown by transport mode)
  - Speed distribution (car speed histogram comparison)
- **Local caching** — Parquet-based cache means you only fetch each date range once

## Setup

1. Clone the repo and create a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install streamlit pandas plotly requests pyarrow python-dotenv
   ```

2. Copy `.env.example` to `.env` and fill in your details:

   ```
   TELRAAM_API_KEY=your_api_key_here
   TELRAAM_SEGMENT_IDS=12345,67890
   ```

   You need a [Telraam API subscription](https://telraam.net/api/data-subscription) and your segment ID(s).

3. Run the app:

   ```bash
   streamlit run app.py
   ```

## Usage

1. Select a segment in the sidebar
2. Load a preset or define your own period groups with date ranges
3. Set time-of-day, day-of-week, and modality filters
4. Click **Load Data**
5. Navigate between chart pages using the sidebar

## Architecture

```
Streamlit UI (app.py + pages/)
        |
Analysis (analysis.py) + Charts (charts.py)
        |
Data access (api_client.py + cache.py)
        |
Telraam REST API + local Parquet cache
```

Each layer only talks to the one below it. Pages never call the API directly. Analysis functions are pure (DataFrame in, DataFrame out, no I/O).
