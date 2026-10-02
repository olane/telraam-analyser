"""Render preview images of the four views using the app's analysis layer.

Why this exists
---------------
A hosted browser (Playwright/Chrome) is often unavailable in agent containers,
so real screenshots can't always be taken. This script instead draws each view
with matplotlib from the *same* pure analysis functions the app uses, producing
representative images without needing the Telraam API or a browser.

It uses synthetic data (clearly labelled) so no API key is required. It is a
developer aid, not a test: for chart regressions see
``tests/test_chart_structure.py``.

Usage
-----
    pip install -e ".[dev]"
    python scripts/render_previews.py                 # -> docs/screenshots/
    python scripts/render_previews.py --out /tmp/pv --dpi 110

Future agents: run the command above, then reference the PNGs from a PR with
raw GitHub URLs, e.g.
https://raw.githubusercontent.com/<owner>/<repo>/<branch>/docs/screenshots/02_trends.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from analysis import (  # noqa: E402
    add_comparison_group,
    compute_daily_totals,
    compute_daily_trend,
    compute_hourly_profile,
    compute_modal_split,
    compute_period_totals,
    compute_speed_distribution,
    compute_speed_trend,
    compute_typical_week,
    compute_weekday_totals,
    describe_instances,
    holiday_vs_term,
    keep_assigned,
    label_periods,
    period_mean_daily,
    weekday_hour_matrix,
)
from charts.theme import KIND_COLOURS, PERIOD_COLOURS  # noqa: E402
from domain.calendars import default_calendar  # noqa: E402
from domain.models import (  # noqa: E402
    ComparisonConfig,
    ComparisonMode,
    Exclusion,
)

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "axes.edgecolor": "#cfd8dc",
        "axes.labelcolor": "#37474f",
        "text.color": "#102027",
        "xtick.color": "#607d8b",
        "ytick.color": "#607d8b",
        "axes.grid": True,
        "grid.color": "#eceff1",
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    }
)

MODALITIES = ["pedestrian", "bike", "car", "heavy"]
CAL = default_calendar()
EXCLUSIONS = [
    Exclusion(
        "A14 roadworks",
        ((pd.Timestamp("2025-10-13").date(), pd.Timestamp("2025-10-17").date()),),
    )
]
WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


# ---------------------------------------------------------------------------
# Synthetic (but realistic) data — no API required
# ---------------------------------------------------------------------------

def build_frame() -> pd.DataFrame:
    index = pd.date_range("2025-09-01", "2026-07-20 23:00", freq="h", tz="UTC")
    hour = index.hour.to_numpy()
    weekday = index.dayofweek.to_numpy()

    holiday_dates = set()
    for instance in CAL.instances:
        if instance.kind.is_holiday:
            for start, end in instance.ranges:
                for day in pd.date_range(start, end, freq="D"):
                    holiday_dates.add(day.date())
    is_holiday = np.array([ts.date() in holiday_dates for ts in index])
    weekend = weekday >= 5

    peak = np.exp(-0.5 * ((hour - 8) / 1.8) ** 2) + 0.9 * np.exp(
        -0.5 * ((hour - 17) / 2.0) ** 2
    )
    daytime = np.clip(np.sin((hour - 6) / 12 * np.pi), 0, None)
    rng = np.random.default_rng(42)

    car = (18 + 175 * peak) * np.where(weekend, 0.45, 1.0) * np.where(is_holiday, 0.68, 1.0)
    bike = (4 + 42 * daytime) * np.where(weekend, 0.9, 1.0) * np.where(is_holiday, 0.85, 1.0)
    ped = (2 + 26 * daytime) * np.where(weekend, 0.8, 1.0) * np.where(is_holiday, 0.9, 1.0)
    heavy = (0.4 + 11 * peak) * np.where(weekend, 0.3, 1.0) * np.where(is_holiday, 0.6, 1.0)

    df = pd.DataFrame(index=index)
    df.index.name = "date"
    df["car"] = np.clip(car * rng.normal(1, 0.08, len(index)), 0, None).round()
    df["bike"] = np.clip(bike * rng.normal(1, 0.12, len(index)), 0, None).round()
    df["pedestrian"] = np.clip(ped * rng.normal(1, 0.12, len(index)), 0, None).round()
    df["heavy"] = np.clip(heavy * rng.normal(1, 0.15, len(index)), 0, None).round()
    df["v85"] = (29 + 4 * weekend + rng.normal(0, 1.8, len(index))).round(1)

    bins = np.arange(0, 130, 5)
    hist = np.exp(-0.5 * ((bins[:-1] + 2.5 - 25.0) / 9) ** 2)
    hist = hist / hist.sum() * 100
    df["car_speed_hist_0to120plus"] = [list(np.round(hist, 2))] * len(index)
    return df


FRAME = build_frame()


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def _visible_ranges(instance, lo, hi):
    """Keep only the ranges overlapping the visible matplotlib x-window."""
    return [
        (start, end)
        for start, end in instance.ranges
        if mdates.date2num(pd.Timestamp(end)) >= lo
        and mdates.date2num(pd.Timestamp(start)) <= hi
    ]


def shade(ax, instances, exclusions=None, xlim=None):
    """Mirror charts/trend.py: terms are lines, holidays/exclusions are bands.

    Ranges outside the clipped data window are skipped so future academic-year
    labels don't float beside the plot.
    """
    if xlim is None:
        lo, hi = ax.get_xlim()
    else:
        lo = mdates.date2num(pd.Timestamp(xlim[0]))
        hi = mdates.date2num(pd.Timestamp(xlim[1]))

    annotated = set()
    for instance in instances:
        ranges = _visible_ranges(instance, lo, hi)
        if not ranges:
            continue
        colour = KIND_COLOURS.get(instance.kind.value, "#7f7f7f")
        if instance.kind.is_term:
            for start, _ in ranges:
                ax.axvline(pd.Timestamp(start), color="#b0bec5", lw=1, ls=":")
            continue
        for start, end in ranges:
            ax.axvspan(pd.Timestamp(start), pd.Timestamp(end), color=colour, alpha=0.18, lw=0)
        if instance.label not in annotated:
            ax.text(
                pd.Timestamp(ranges[0][0]), 1.0, f" {instance.label}",
                transform=ax.get_xaxis_transform(), fontsize=7, color=colour,
                va="bottom", ha="left",
            )
            annotated.add(instance.label)
    for exclusion in exclusions or []:
        for start, end in exclusion.ranges:
            ax.axvspan(pd.Timestamp(start), pd.Timestamp(end), color="#b0bec5", alpha=0.45, lw=0)
        if exclusion.ranges:
            ax.text(
                pd.Timestamp(exclusion.ranges[0][0]), 0.02,
                f" Excluded: {exclusion.label}",
                transform=ax.get_xaxis_transform(), fontsize=7, color="#546e7a",
                va="bottom", ha="left",
            )


def titled(ax, title):
    ax.set_title(title, loc="left", fontsize=12, fontweight="bold", pad=10)


def save(fig, out_dir: Path, name: str, dpi: int):
    path = out_dir / name
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print("wrote", path)


def styled_table(ax, rows, bbox, col_widths):
    table = ax.table(
        cellText=rows, loc="upper left", bbox=bbox,
        cellLoc="right", colWidths=col_widths,
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor("#e3e8ee")
        if r == 0:
            cell.set_facecolor("#0b6e99")
            cell.set_text_props(color="white", fontweight="bold")


# ---------------------------------------------------------------------------
# The four views
# ---------------------------------------------------------------------------

def render_overview(out_dir: Path, dpi: int):
    assigned = keep_assigned(label_periods(FRAME, holiday_vs_term(CAL)))
    totals = compute_period_totals(assigned, MODALITIES)
    mean_daily = period_mean_daily(assigned, MODALITIES)
    delta = (
        (mean_daily["School holidays"] - mean_daily["Term time"])
        / mean_daily["Term time"]
        * 100
    )
    overall = compute_daily_totals(assigned, MODALITIES)[MODALITIES].sum(axis=1).mean()

    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.axis("off")
    ax.set_title("Telraam Traffic Explorer — Overview", loc="left",
                 fontsize=16, fontweight="bold")

    kpis = [
        ("Hourly rows", f"{len(FRAME):,}"),
        ("Groups", "2"),
        ("Mean daily count", f"{overall:,.0f}"),
        ("Holidays vs term", f"{delta:+.1f}%"),
    ]
    for i, (label, value) in enumerate(kpis):
        x = 0.02 + i * 0.245
        ax.add_patch(plt.Rectangle((x, 0.72), 0.22, 0.19, transform=ax.transAxes,
                                   facecolor="#f7fafc", edgecolor="#e3e8ee"))
        ax.text(x + 0.015, 0.86, label, transform=ax.transAxes, fontsize=9, color="#607d8b")
        ax.text(x + 0.015, 0.77, value, transform=ax.transAxes, fontsize=16,
                color="#0b6e99", fontweight="bold")

    ax.text(0.02, 0.63, "Totals by period (selected modalities)", transform=ax.transAxes,
            fontsize=11, fontweight="bold")
    rows = [["Period", "Pedestrians", "Cycles", "Cars", "Heavy", "Total"]]
    for _, row in totals.iterrows():
        rows.append([
            row.period_label, f"{row.pedestrian:,.0f}", f"{row.bike:,.0f}",
            f"{row.car:,.0f}", f"{row.heavy:,.0f}", f"{row.total:,.0f}",
        ])
    styled_table(ax, rows, [0.02, 0.08, 0.96, 0.5], [0.28, 0.16, 0.14, 0.14, 0.14, 0.14])
    save(fig, out_dir, "01_overview.png", dpi)


def _term_grouped_assigned():
    """Rows bucketed as Term time vs School holidays (the default axis)."""
    labelled = label_periods(FRAME, holiday_vs_term(CAL))
    grouped = add_comparison_group(
        labelled, ComparisonConfig(mode=ComparisonMode.HOLIDAY_VS_TERM)
    )
    return grouped[grouped["group_label"].notna()]


def render_trends(out_dir: Path, dpi: int):
    trend = compute_daily_trend(FRAME, MODALITIES, window=7)
    assigned = _term_grouped_assigned()
    typical = compute_typical_week(
        assigned, MODALITIES, group_col="group_label"
    )
    groups = list(dict.fromkeys(assigned["group_label"].dropna()))
    matrices = [
        (group, weekday_hour_matrix(typical, group, "car", group_col="group_label"))
        for group in groups
    ]
    speed = compute_speed_distribution(FRAME, unit="mph")
    v85 = compute_speed_trend(FRAME, unit="mph")

    fig = plt.figure(figsize=(12, 15))
    gs = fig.add_gridspec(
        3, 2, height_ratios=[1.0, 1.0, 1.0], hspace=0.55, wspace=0.25
    )

    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(trend["day"], trend["total"], color="#b0bec5", lw=1, label="Daily total")
    ax1.plot(trend["day"], trend["rolling"], color="#0b6e99", lw=2.6, label="7-day average")
    xlim = (FRAME.index.min(), FRAME.index.max())
    shade(ax1, CAL.instances, EXCLUSIONS, xlim=xlim)
    titled(ax1, "Traffic trend — clipped to loaded data")
    ax1.set_ylabel("Count per day")
    ax1.set_xlim(*xlim)
    ax1.legend(loc="upper right", frameon=False, ncol=2)
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

    for i, (group, matrix) in enumerate(matrices[:2]):
        ax = fig.add_subplot(gs[1, i])
        ax.imshow(matrix.values, aspect="auto", cmap="Blues")
        ax.set_yticks(range(7))
        ax.set_yticklabels(list(matrix.index))
        ax.set_xticks(range(0, 24, 3))
        ax.set_xticklabels(list(range(0, 24, 3)))
        titled(ax, f"Typical week — {group}, cars")
        ax.set_xlabel("Hour of day")
        ax.grid(False)

    ax3 = fig.add_subplot(gs[2, 0])
    bin_cols = list(speed.columns)
    row = speed.iloc[0]
    ax3.bar(np.arange(len(bin_cols)), [row[c] for c in bin_cols], 0.7,
            color="#0b6e99")
    ax3.set_xticks(np.arange(len(bin_cols)))
    ax3.set_xticklabels(bin_cols, rotation=45, ha="right", fontsize=7)
    titled(ax3, "Car speed distribution (mph)")
    ax3.set_ylabel("Share (%)")

    ax4 = fig.add_subplot(gs[2, 1])
    ax4.plot(v85["day"], v85["v85"], color="#b0bec5", lw=1, label="Daily V85")
    ax4.plot(v85["day"], v85["rolling"], color="#c46210", lw=2.4,
             label="7-day average")
    titled(ax4, "V85 trend (mph)")
    ax4.set_ylabel("V85 (mph)")
    ax4.legend(frameon=False)

    fig.suptitle("Telraam Traffic Explorer — Trends", x=0.02, ha="left",
                 fontsize=16, fontweight="bold")
    save(fig, out_dir, "02_trends.png", dpi)


def render_compare(out_dir: Path, dpi: int):
    assigned = _term_grouped_assigned()
    daily = compute_daily_totals(assigned, MODALITIES, group_col="group_label")
    weekday_df = compute_weekday_totals(
        daily, MODALITIES, group_col="group_label"
    )
    profile = compute_hourly_profile(
        assigned, MODALITIES, group_col="group_label"
    )
    split = compute_modal_split(assigned, MODALITIES, group_col="group_label")
    groups = list(dict.fromkeys(weekday_df["group_label"]))

    fig = plt.figure(figsize=(12, 9))
    gs = fig.add_gridspec(2, 2, hspace=0.4, wspace=0.25)

    ax1 = fig.add_subplot(gs[0, 0])
    x = np.arange(7)
    for i, group in enumerate(groups):
        subset = weekday_df[weekday_df["group_label"] == group].set_index("weekday")
        values = [subset.car.get(d, 0) for d in range(7)]
        ax1.bar(x + (i - 0.5) * 0.38, values, 0.38, label=group,
                color=PERIOD_COLOURS[i % len(PERIOD_COLOURS)])
    ax1.set_xticks(x)
    ax1.set_xticklabels(WEEKDAY_LABELS)
    titled(ax1, "Cars by weekday")
    ax1.legend(frameon=False)

    ax2 = fig.add_subplot(gs[0, 1])
    for group in groups:
        subset = profile[profile["group_label"] == group].sort_values("hour")
        ax2.plot(subset.hour, subset.car, marker="o", ms=3, label=group,
                 color=PERIOD_COLOURS[groups.index(group) % len(PERIOD_COLOURS)])
    titled(ax2, "Average hour of day — cars")
    ax2.set_xlabel("Hour")
    ax2.legend(frameon=False)

    ax3 = fig.add_subplot(gs[1, 0])
    xm = np.arange(len(MODALITIES))
    for i, group in enumerate(groups):
        row = split[split["group_label"] == group].iloc[0]
        ax3.bar(xm + (i - 0.5) * 0.38, [row[m] for m in MODALITIES], 0.38,
                label=group, color=PERIOD_COLOURS[i % len(PERIOD_COLOURS)])
    ax3.set_xticks(xm)
    ax3.set_xticklabels([m.title() for m in MODALITIES])
    titled(ax3, "Modal split (%)")
    ax3.legend(frameon=False)

    ax4 = fig.add_subplot(gs[1, 1])
    for i, group in enumerate(groups):
        subset = profile[profile["group_label"] == group].sort_values("hour")
        ax4.plot(subset.hour, subset.bike, marker="o", ms=3, label=group,
                 color=PERIOD_COLOURS[i % len(PERIOD_COLOURS)])
    titled(ax4, "Average hour of day — cycles")
    ax4.set_xlabel("Hour")
    ax4.legend(frameon=False)

    fig.suptitle("Telraam Traffic Explorer — Compare (term time vs holidays)",
                 x=0.02, ha="left", fontsize=16, fontweight="bold")
    save(fig, out_dir, "03_compare.png", dpi)


def render_detail(out_dir: Path, dpi: int):
    instances = holiday_vs_term(CAL)
    grouped = _term_grouped_assigned()
    totals = compute_period_totals(grouped, MODALITIES, group_col="group_label")
    split = compute_modal_split(grouped, MODALITIES, group_col="group_label")

    fig = plt.figure(figsize=(12, 9))
    gs = fig.add_gridspec(3, 1, hspace=0.55)

    ax1 = fig.add_subplot(gs[0])
    ax1.axis("off")
    titled(ax1, "Periods")
    periods = describe_instances(instances)
    rows = [["Period", "Type", "Year", "Start", "End", "Days"]]
    for _, r in periods.iterrows():
        rows.append([
            r.Period, r.Type, r.Year or "", str(r.Start), str(r.End), int(r.Days),
        ])
    styled_table(
        ax1, rows, [0.0, 0.06, 1.0, 0.62],
        [0.22, 0.22, 0.12, 0.16, 0.16, 0.1],
    )

    ax2 = fig.add_subplot(gs[1])
    ax2.axis("off")
    titled(ax2, "Totals by group")
    rows = [["Group", "Pedestrians", "Cycles", "Cars", "Heavy", "Total"]]
    for _, r in totals.iterrows():
        rows.append([
            r.group_label, f"{r.pedestrian:,.0f}", f"{r.bike:,.0f}",
            f"{r.car:,.0f}", f"{r.heavy:,.0f}", f"{r.total:,.0f}",
        ])
    styled_table(
        ax2, rows, [0.0, 0.03, 1.0, 0.55],
        [0.28, 0.16, 0.14, 0.14, 0.14, 0.14],
    )

    ax3 = fig.add_subplot(gs[2])
    ax3.axis("off")
    titled(ax3, "Modal split (%)")
    rows = [["Group", *[m.title() for m in MODALITIES]]]
    for _, r in split.iterrows():
        rows.append([r.group_label, *[f"{r[m]:.1f}" for m in MODALITIES]])
    styled_table(
        ax3, rows, [0.0, 0.03, 1.0, 0.5],
        [0.28, 0.18, 0.18, 0.18, 0.18],
    )
    ax3.text(0.0, -0.3, "Only derived aggregates are exportable.\n"
             "Raw Telraam data is CC BY-NC 4.0.",
             fontsize=9, color="#607d8b", transform=ax3.transAxes)

    fig.suptitle("Telraam Traffic Explorer — Detail", x=0.02, ha="left",
                 fontsize=16, fontweight="bold")
    save(fig, out_dir, "04_detail.png", dpi)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(REPO / "docs" / "screenshots"),
                        help="Output directory (default: docs/screenshots)")
    parser.add_argument("--dpi", type=int, default=135, help="Image DPI")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Rendering previews (synthetic data) to {out_dir}")

    render_overview(out_dir, args.dpi)
    render_trends(out_dir, args.dpi)
    render_compare(out_dir, args.dpi)
    render_detail(out_dir, args.dpi)
    print("done")


if __name__ == "__main__":
    main()
