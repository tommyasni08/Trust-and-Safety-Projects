import pandas as pd
from typing import Iterable, Tuple
from config import DATA_DIR, KPIS_CSV

CAT_SHARE_COLS = [
    "share_spam","share_harassment_hate","share_nudity",
    "share_misinformation","share_child_safety","share_other"
]
SRC_SHARE_COLS = ["share_user","share_ai","share_trusted"]

# Raw counts that define enforcement mix (denominator = enforcements)
ENF_COUNT_COLS = ["enf_removed","enf_warning","enf_suspension","enf_downrank"]

def country_kpi_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Core funnel + response: average rates by country.
    """
    cols = ["report_rate","enforcement_rate","appeal_success_rate","median_response_time_hours"]
    out = (df.groupby("country")[cols]
             .mean()
             .reset_index())
    return out.round(3)

def country_category_mix(df: pd.DataFrame) -> pd.DataFrame:
    """
    Average category shares (of reports) by country.
    """
    out = (df.groupby("country")[CAT_SHARE_COLS]
             .mean()
             .reset_index())
    return out.round(3)

def country_source_mix(df: pd.DataFrame) -> pd.DataFrame:
    """
    Average source shares (of reports) by country.
    """
    out = (df.groupby("country")[SRC_SHARE_COLS]
             .mean()
             .reset_index())
    return out.round(3)

def country_enforcement_mix(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enforcement type proportions by country.
    Denominator is total 'enforcements' (not reports).
    """
    grp = df.groupby("country", as_index=False)[ENF_COUNT_COLS + ["enforcements"]].sum()
    # Avoid division by zero
    for c in ENF_COUNT_COLS:
        grp[c] = grp[c] / grp["enforcements"].where(grp["enforcements"] > 0, other=pd.NA)
    # Rename to *_share for clarity
    rename_map = {
        "enf_removed": "enf_removed_share",
        "enf_warning": "enf_warning_share",
        "enf_suspension": "enf_suspension_share",
        "enf_downrank": "enf_downrank_share",
    }
    out = grp[["country"] + ENF_COUNT_COLS].rename(columns=rename_map)
    return out.round(3)

def sla_summary(df: pd.DataFrame, thresholds: Tuple[float,float]=(12.0, 24.0)) -> pd.DataFrame:
    """
    Share of days meeting response-time thresholds per country.
    thresholds: (tight, broad) e.g., (12h, 24h)
    """
    tight, broad = thresholds
    tmp = df.assign(
        meet_tight = (df["median_response_time_hours"] <= tight),
        meet_broad = (df["median_response_time_hours"] <= broad),
    )
    out = (tmp.groupby("country")[["meet_tight","meet_broad"]]
             .mean()
             .reset_index()
             .rename(columns={"meet_tight": f"pct_days_resp_<=_{int(tight)}h",
                              "meet_broad": f"pct_days_resp_<=_{int(broad)}h"}))
    return out.round(3)

def save_country_kpis(df: pd.DataFrame):
    """
    Save a single wide CSV with core KPIs + mixes + SLA.
    """
    core = country_kpi_summary(df)
    cat  = country_category_mix(df)
    src  = country_source_mix(df)
    enf  = country_enforcement_mix(df)
    sla  = sla_summary(df, thresholds=(12.0, 24.0))

    # Merge all on 'country'
    out = (core.merge(cat, on="country", how="left")
                .merge(src, on="country", how="left")
                .merge(enf, on="country", how="left")
                .merge(sla, on="country", how="left"))

    path = DATA_DIR / KPIS_CSV
    out.to_csv(path, index=False)
    return path

def add_rolling(
    df: pd.DataFrame,
    cols: Iterable[str] = ("reports","enforcements","median_response_time_hours"),
    window: int = 7
) -> pd.DataFrame:
    """
    Add grouped rolling means per country for the provided columns.
    Example: add_rolling(df, cols=["reports","share_misinformation"])
    """
    df = df.sort_values(["country","date"]).copy()
    for col in cols:
        roll_name = f"{col}_roll{window}"
        df[roll_name] = df.groupby("country")[col].transform(lambda s: s.rolling(window, min_periods=1).mean())
    return df
