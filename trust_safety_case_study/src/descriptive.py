import pandas as pd
from typing import List

# Columns introduced by the richer generator
CAT_COUNT_COLS: List[str] = [
    "reports_spam","reports_harassment_hate","reports_nudity",
    "reports_misinformation","reports_child_safety","reports_other"
]
CAT_SHARE_COLS: List[str] = [
    "share_spam","share_harassment_hate","share_nudity",
    "share_misinformation","share_child_safety","share_other"
]
SRC_SHARE_COLS: List[str] = ["share_user","share_ai","share_trusted"]
ENF_COUNT_COLS: List[str] = ["enf_removed","enf_warning","enf_suspension","enf_downrank"]

def overall_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    High-level numeric summary (exclude non-numeric to avoid warnings).
    """
    num = df.select_dtypes(include="number")
    return num.describe().round(2).T  # transpose for readability

def country_aggregates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Core operational averages by country (volumes + KPI rates).
    """
    cols = [
        "active_users","content_created","reports","enforcements",
        "appeals","successful_appeals","median_response_time_hours",
        "report_rate","enforcement_rate","appeal_success_rate",
    ]
    return (
        df.groupby("country")[cols]
          .mean()
          .round(2)
          .reset_index()
    )

def country_category_totals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sum of category-specific report counts by country (6-month total).
    Useful for absolute scale comparisons.
    """
    return (
        df.groupby("country")[CAT_COUNT_COLS]
          .sum()
          .reset_index()
    )

def country_category_share_means(df: pd.DataFrame) -> pd.DataFrame:
    """
    Average category shares of reports by country (0–1).
    Useful to say 'spam drives X% of reports in country Y'.
    """
    return (
        df.groupby("country")[CAT_SHARE_COLS]
          .mean()
          .round(3)
          .reset_index()
    )

def country_source_share_means(df: pd.DataFrame) -> pd.DataFrame:
    """
    Average report-source shares by country (0–1) — user vs AI vs trusted.
    """
    return (
        df.groupby("country")[SRC_SHARE_COLS]
          .mean()
          .round(3)
          .reset_index()
    )

def country_enforcement_totals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sum of enforcement-type counts by country (absolute volumes).
    Enforcement *shares* are covered in kpis.country_enforcement_mix().
    """
    return (
        df.groupby("country")[ENF_COUNT_COLS + ["enforcements"]]
          .sum()
          .reset_index()
    )

def dominant_category_by_country(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each country, which category has the highest average share?
    Returns: country, dominant_category, dominant_share
    """
    share_means = df.groupby("country")[CAT_SHARE_COLS].mean()
    idx = share_means.values.argmax(axis=1)
    dom_cat = [CAT_SHARE_COLS[i].replace("share_", "") for i in idx]
    dom_share = share_means.max(axis=1).round(3)
    out = share_means.reset_index()[["country"]].copy()
    out["dominant_category"] = dom_cat
    out["dominant_share"] = dom_share
    return out
