import os
from pathlib import Path
from typing import Iterable, Tuple, List

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# ---- Visual polish (colors, grids, spacing) ----
plt.rcParams.update({
    "axes.facecolor": "#FFFFFF",
    "figure.facecolor": "#FFFFFF",
    "axes.edgecolor": "#94A3B8",
    "axes.labelcolor": "#0F172A",
    "xtick.color": "#334155",
    "ytick.color": "#334155",
    "grid.color": "#E2E8F0",
    "grid.linestyle": "-",
    "grid.linewidth": 0.6,
})

# ----------------------------
# Paths / constants
# ----------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
IMAGES_DIR = ROOT / "images"
CSV_PATH = DATA_DIR / "tiktok_ts_apac_daily.csv"

ANOMALY_DEFAULT_WINDOW = 7
ANOMALY_DEFAULT_Z = 2.0

CAT_SHARE_COLS: List[str] = [
    "share_spam","share_harassment_hate","share_nudity",
    "share_misinformation","share_child_safety","share_other"
]
SRC_SHARE_COLS: List[str] = ["share_user","share_ai","share_trusted"]
ENF_COUNT_COLS: List[str] = ["enf_removed","enf_warning","enf_suspension","enf_downrank"]

# Semantic color maps (fixed palette for readability)
CAT_COLOR_MAP = {
    "share_spam": "#64748B",              # blue-gray
    "share_harassment_hate": "#7C3AED",   # purple
    "share_nudity": "#DB2777",            # magenta
    "share_misinformation": "#E69F00",    # Okabe–Ito orange
    "share_child_safety": "#DC2626",      # red (use sparingly)
    "share_other": "#94A3B8",             # slate
}
SRC_COLOR_MAP = {
    "share_user": "#2563EB",              # blue
    "share_ai": "#0D9488",                # teal
    "share_trusted": "#009E73",           # green
}
ENF_COLOR_MAP = {
    "enf_removed": "#DC2626",             # red
    "enf_warning": "#F59E0B",             # amber
    "enf_suspension": "#B91C1C",          # deep red
    "enf_downrank": "#475569",            # slate
}

# ----------------------------
# Utilities
# ----------------------------
@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH, parse_dates=["date"])
    # Safety: ensure expected columns exist
    expected = {
        "date","country","active_users","content_created","reports","enforcements",
        "appeals","successful_appeals","median_response_time_hours",
        "report_rate","enforcement_rate","appeal_rate","appeal_success_rate",
        "reports_spam","reports_harassment_hate","reports_nudity","reports_misinformation",
        "reports_child_safety","reports_other",
        "reports_user","reports_ai","reports_trusted",
        "enf_removed","enf_warning","enf_suspension","enf_downrank",
        # shares (derived)
        "share_spam","share_harassment_hate","share_nudity","share_misinformation",
        "share_child_safety","share_other","share_user","share_ai","share_trusted",
    }
    missing = expected - set(df.columns)
    if missing:
        st.warning(f"Dataset is missing expected columns: {sorted(missing)}")
    return df


def apply_filters(df: pd.DataFrame, countries: List[str], date_range: Tuple[pd.Timestamp, pd.Timestamp]) -> pd.DataFrame:
    if countries:
        df = df[df["country"].isin(countries)]
    if date_range:
        start, end = date_range
        df = df[(df["date"] >= start) & (df["date"] <= end)]
    return df.sort_values(["country", "date"]).reset_index(drop=True)


def add_rolling(df: pd.DataFrame, cols: Iterable[str], window: int = 7) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.sort_values(["country","date"]).copy()
    for col in cols:
        roll = df.groupby("country")[col].transform(lambda s: s.rolling(window, min_periods=1).mean())
        df[f"{col}_roll{window}"] = roll
    return df


def kpi_block(df: pd.DataFrame, sla_hours_tight: float = 12.0, sla_hours_broad: float = 24.0) -> dict:
    """Compute core KPIs from the filtered slice (use proper denominators)."""
    if df.empty:
        return dict(
            content_created=0, reports=0, enforcements=0, appeals=0,
            report_rate=np.nan, enforcement_rate=np.nan, appeal_success_rate=np.nan,
            resp_hours=np.nan, sla_tight=np.nan, sla_broad=np.nan
        )
    sums = df[["content_created","reports","enforcements","appeals","successful_appeals"]].sum()
    kpis = {
        "content_created": int(sums["content_created"]),
        "reports": int(sums["reports"]),
        "enforcements": int(sums["enforcements"]),
        "appeals": int(sums["appeals"]),
        "report_rate": (sums["reports"] / sums["content_created"]) if sums["content_created"] > 0 else np.nan,
        "enforcement_rate": (sums["enforcements"] / sums["reports"]) if sums["reports"] > 0 else np.nan,
        "appeal_success_rate": (sums["successful_appeals"] / sums["appeals"]) if sums["appeals"] > 0 else np.nan,
        "resp_hours": df["median_response_time_hours"].mean(),
    }
    # SLA: share of rows (country-days) meeting thresholds within filtered scope
    kpis["sla_tight"] = (df["median_response_time_hours"] <= sla_hours_tight).mean() if not df.empty else np.nan
    kpis["sla_broad"] = (df["median_response_time_hours"] <= sla_hours_broad).mean() if not df.empty else np.nan
    return kpis


def fmt_pct(x: float) -> str:
    return "—" if pd.isna(x) else f"{x*100:,.1f}%"


def draw_line(df: pd.DataFrame, xcol: str, ycols: List[str], title: str, ylabel: str, legend: bool = True, fname: str = None):
    plt.figure(figsize=(10, 5))
    for c in ycols:
        if c in df.columns:
            plt.plot(df[xcol], df[c], label=c)
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel(ylabel)
    if legend:
        plt.legend()
    st.pyplot(plt.gcf())
    plt.close()


def draw_bars(x: List[str], ys: List[float], title: str, ylabel: str, fname: str = None):
    plt.figure(figsize=(8, 5))
    plt.bar(x, ys)
    plt.title(title)
    plt.xlabel("Country")
    plt.ylabel(ylabel)
    st.pyplot(plt.gcf())
    plt.close()

def draw_stacked_100_bars(df: pd.DataFrame, index_col: str, parts: List[str], title: str, color_map: dict):
    """
    Draw 100% stacked bars: per index (e.g., country), show composition of 'parts' columns summing to 1.
    Expects values already in [0,1]. Handles NaNs by treating them as zeros.
    """
    X = df[index_col].tolist()
    Y = [df[p].fillna(0.0).tolist() for p in parts]
    colors = [color_map.get(p, None) for p in parts]

    plt.figure(figsize=(10, 5))
    bottom = np.zeros(len(X))
    for y, p, color in zip(Y, parts, colors):
        plt.bar(X, y, bottom=bottom, label=p, color=color)
        bottom = bottom + np.array(y)

    ax = plt.gca()
    ax.grid(True, axis="y")
    plt.title(title)
    plt.xlabel(index_col.capitalize())
    plt.ylabel("Share (100%)")
    plt.ylim(0, 1)
    plt.legend()
    st.pyplot(plt.gcf())
    plt.close()


# ----------------------------
# Anomaly helpers (simple rolling z)
# ----------------------------
def rolling_z(series: pd.Series, window: int = 7) -> Tuple[pd.Series, pd.Series]:
    m = series.rolling(window, min_periods=1).mean()
    s = series.rolling(window, min_periods=1).std().replace(0, np.nan)
    return m, s

def detect_z_anomalies(df: pd.DataFrame, metric_col: str, window: int = 7, z: float = 2.0) -> pd.DataFrame:
    """Return rows with columns: date, country, metric, value, zscore, anomaly."""
    out = []
    for c in df["country"].unique():
        s = df[df["country"] == c].sort_values("date")
        if metric_col not in s.columns:
            continue
        m, sd = rolling_z(s[metric_col], window)
        zscores = (s[metric_col] - m) / sd
        anomalies = zscores.abs() > z
        tmp = pd.DataFrame({
            "date": s["date"].values,
            "country": c,
            "metric": metric_col,
            "value": s[metric_col].values,
            "zscore": zscores.values,
            "anomaly": anomalies.values
        })
        out.append(tmp)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=["date","country","metric","value","zscore","anomaly"])


# ----------------------------
# Streamlit UI
# ----------------------------
st.set_page_config(page_title="Trust & Safety Dashboard (Synthetic)", layout="wide")
st.markdown("""
<style>
.block-container { padding-top: 1rem; padding-bottom: 2rem; }
[data-testid="stMetricValue"] { font-weight: 700; }
.small-note { color:#64748B; font-size: 0.9rem; }
.badge { display:inline-block; padding:2px 8px; border-radius: 999px; font-size: 0.75rem; }
.badge-critical { background:#FEE2E2; color:#B91C1C; }
.badge-warning  { background:#FEF3C7; color:#92400E; }
</style>
""", unsafe_allow_html=True)
st.title("Trust & Safety Dashboard — Synthetic APAC (Mar–Aug 2025)")

# Sidebar filters
df_all = load_data()
all_countries = sorted(df_all["country"].unique().tolist()) if not df_all.empty else []
st.sidebar.header("Filters")

countries_sel = st.sidebar.multiselect("Countries", all_countries, default=all_countries)
date_min = df_all["date"].min() if not df_all.empty else pd.Timestamp("2025-03-01")
date_max = df_all["date"].max() if not df_all.empty else pd.Timestamp("2025-08-31")
date_range = st.sidebar.date_input("Date range", value=(date_min, date_max), min_value=date_min, max_value=date_max)

# Anomaly controls (used in the Anomalies tab)
st.sidebar.header("Anomaly Controls")
an_window = st.sidebar.number_input("Rolling window (days)", min_value=3, max_value=30, value=ANOMALY_DEFAULT_WINDOW, step=1)
an_z = st.sidebar.slider("Z-score threshold", min_value=1.0, max_value=4.0, value=ANOMALY_DEFAULT_Z, step=0.1)

# Filtered data + add rollings for selected trend cols
df_f = apply_filters(df_all, countries_sel, tuple(pd.to_datetime(date_range)) if isinstance(date_range, tuple) else (date_min, date_max))
trend_cols = ["reports","enforcements","median_response_time_hours","share_misinformation","share_user"]
df_f = add_rolling(df_f, trend_cols, window=7)

# Tabs
tabs = st.tabs(["Overview", "Content Mix", "Sources", "Enforcement", "Anomalies", "Data"])

# --------------------------------
# 1) OVERVIEW
# --------------------------------
with tabs[0]:
    st.subheader("Overview")
    k = kpi_block(df_f)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Content Created", f"{k['content_created']:,}")
    c2.metric("Reports", f"{k['reports']:,}", delta=None)
    c3.metric("Enforcements", f"{k['enforcements']:,}")
    c4.metric("Appeals", f"{k['appeals']:,}")
    c5.metric("Median Response (hrs)", f"{k['resp_hours']:.1f}" if not pd.isna(k['resp_hours']) else "—")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Report Rate", fmt_pct(k["report_rate"]))
    c2.metric("Enforcement Rate", fmt_pct(k["enforcement_rate"]))
    c3.metric("Appeal Success Rate", fmt_pct(k["appeal_success_rate"]))
    c4.metric("Days ≤12h Response", fmt_pct(k["sla_tight"]))
    c5.metric("Days ≤24h Response", fmt_pct(k["sla_broad"]))

    st.divider()

    # Trends
    st.markdown("**Daily reports (7d rolling overlay)**")
    # Compute country-mean trend for compactness
    if not df_f.empty:
        plot_df = (df_f.groupby("date")[["reports","reports_roll7"]].mean().reset_index())
        draw_line(plot_df, "date", ["reports","reports_roll7"], "Daily Reports (Mean across selected countries)", "Reports")

    st.markdown("**Totals (selected period)**")
    if not df_f.empty:
        totals = df_f.groupby("country")[["reports","enforcements"]].sum().reset_index()
        x = totals["country"].tolist()
        y1 = totals["reports"].tolist()
        y2 = totals["enforcements"].tolist()

        # Draw side-by-side bars with matplotlib (two calls)
        plt.figure(figsize=(8,5))
        idx = np.arange(len(x))
        w = 0.35
        plt.bar(idx, y1, width=w, label="Reports")
        plt.bar(idx+w, y2, width=w, label="Enforcements")
        plt.xticks(idx+w/2, x)
        plt.title("Totals by Country (Selected Period)")
        plt.xlabel("Country"); plt.ylabel("Count"); plt.legend()
        st.pyplot(plt.gcf()); plt.close()
    else:
        st.info("No data in the current filter selection.")


# --------------------------------
# 2) CONTENT MIX (Categories)
# --------------------------------
with tabs[1]:
    st.subheader("Content Mix — Categories")
    if df_f.empty:
        st.info("No data to display for current filters.")
    else:
        # Average category shares by country
        avg_cat = (df_f.groupby("country")[CAT_SHARE_COLS].mean().reset_index())

        st.markdown("**Average category shares by country (100% stacked)**")
        draw_stacked_100_bars(avg_cat, "country", CAT_SHARE_COLS,
                            title="Category Composition of Reports by Country",
                            color_map=CAT_COLOR_MAP)

        # Trend of share_misinformation (avg across selected countries)
        st.markdown("**Trend: share_misinformation (7d rolling if available)**")
        col_to_plot = "share_misinformation_roll7" if "share_misinformation_roll7" in df_f.columns else "share_misinformation"
        mis = (df_f.groupby("date")[col_to_plot].mean().reset_index())
        draw_line(mis, "date", [col_to_plot], "Misinformation Share Trend (avg across selected countries)", "Share")
        st.markdown('<div class="small-note">Mean across selected countries; shaded areas can indicate real-world events in future iterations.</div>', unsafe_allow_html=True)


# --------------------------------
# 3) SOURCES
# --------------------------------
with tabs[2]:
    st.subheader("Report Sources")
    if df_f.empty:
        st.info("No data to display for current filters.")
    else:
        avg_src = (df_f.groupby("country")[SRC_SHARE_COLS].mean().reset_index())

        st.markdown("**Average report-source shares by country (100% stacked)**")
        draw_stacked_100_bars(avg_src, "country", SRC_SHARE_COLS,
                            title="Source Composition of Reports by Country",
                            color_map=SRC_COLOR_MAP)

        # Trend of source shares (avg across countries, 7d roll where available)
        st.markdown("**Trend: source shares (7d rolling if available)**")
        cols = []
        for base in SRC_SHARE_COLS:
            roll = f"{base}_roll7"
            cols.append(roll if roll in df_f.columns else base)
        src_trend = (df_f.groupby("date")[cols].mean().reset_index())
        draw_line(src_trend, "date", cols, "Report Source Share Trend (avg across selected countries)", "Share")
        st.markdown('<div class="small-note">Trusted flaggers often imply higher severity; expect lower appeal success in their segments.</div>', unsafe_allow_html=True)


# --------------------------------
# 4) ENFORCEMENT
# --------------------------------
with tabs[3]:
    st.subheader("Enforcement")
    if df_f.empty:
        st.info("No data to display for current filters.")
    else:
        # Enforcement mix shares: denominator = enforcements (aggregate in selection)
        sums = df_f.groupby("country")[ENF_COUNT_COLS + ["enforcements"]].sum().reset_index()
        for c in ENF_COUNT_COLS:
            sums[c] = (sums[c] / sums["enforcements"].where(sums["enforcements"] > 0, np.nan))
        sums[ENF_COUNT_COLS] = sums[ENF_COUNT_COLS].fillna(0.0)

        st.markdown("**Enforcement mix by country (100% stacked)**")
        draw_stacked_100_bars(sums, "country", ENF_COUNT_COLS,
                            title="Enforcement Type Composition by Country (Share of Enforcements)",
                            color_map=ENF_COLOR_MAP)

        # Coverage & fairness KPIs for context (computed on filtered scope)
        st.markdown("**Coverage & Fairness (selected period)**")
        denom_reports = df_f["reports"].sum()
        denom_enf = df_f["enforcements"].sum()
        denom_app = df_f["appeals"].sum()
        er = (denom_enf / denom_reports) if denom_reports > 0 else np.nan
        asr = (df_f["successful_appeals"].sum() / denom_app) if denom_app > 0 else np.nan
        c1, c2 = st.columns(2)
        c1.metric("Enforcement Rate", fmt_pct(er))
        c2.metric("Appeal Success Rate", fmt_pct(asr))
        st.markdown('<div class="small-note">Mix is normalized by enforcements, not reports, to reflect action composition.</div>', unsafe_allow_html=True)


# --------------------------------
# 5) ANOMALIES
# --------------------------------
with tabs[4]:
    st.subheader("Anomalies")
    if df_f.empty:
        st.info("No data to analyze for current filters.")
    else:
        st.caption("Method: rolling z-score over a 7-day window by default; flag |z| > threshold.")

        # Metrics to check
        metrics_to_check = ["reports", "share_misinformation", "share_child_safety", "share_user"]
        # Compute anomalies for current filtered scope per country
        parts = []
        for m in metrics_to_check:
            tmp = detect_z_anomalies(df_f, metric_col=m, window=an_window, z=an_z)
            parts.append(tmp)
        an = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()

        # Filter anomalies to only flagged rows
        flagged = an[an["anomaly"]].copy()
        st.markdown("**Flagged anomalies (in current filters):**")
        if flagged.empty:
            st.success("No anomalies under the current settings.")
        else:
            # Show a compact table
            show_cols = ["date","country","metric","value","zscore"]
            flagged_sorted = flagged.sort_values(["date","country","metric"], ascending=[True, True, True])
            st.dataframe(flagged_sorted[show_cols].reset_index(drop=True), use_container_width=True, height=300)

        # Plot: reports + anomalies for one selected country
        st.markdown("**Example plot: Reports + anomaly markers**")
        ctry = st.selectbox("Country for example plot", options=sorted(df_f["country"].unique().tolist()))
        s = df_f[df_f["country"] == ctry].sort_values("date")
        res = an[(an["country"] == ctry) & (an["metric"] == "reports")]

        plt.figure(figsize=(10,5))
        plt.plot(s["date"], s["reports"], label="Reports")
        # mark anomalies
        if not res.empty:
            flagged_rows = res[res["anomaly"]]
            if not flagged_rows.empty:
                plt.scatter(flagged_rows["date"], flagged_rows["value"], s=40)
        plt.title(f"Reports & Anomalies — {ctry}")
        plt.xlabel("Date"); plt.ylabel("Reports"); plt.legend()
        st.pyplot(plt.gcf()); plt.close()


# --------------------------------
# 6) DATA
# --------------------------------
with tabs[5]:
    st.subheader("Data (Filtered)")
    if df_f.empty:
        st.info("No rows in current selection.")
    else:
        st.dataframe(df_f, use_container_width=True, height=420)

        # CSV download of filtered data
        csv_bytes = df_f.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download filtered CSV",
            data=csv_bytes,
            file_name="ts_filtered_export.csv",
            mime="text/csv",
        )

st.caption("© Synthetic dataset for portfolio demonstration. No real user data.")
