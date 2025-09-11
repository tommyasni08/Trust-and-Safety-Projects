import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from config import IMAGES_DIR

def save_fig(name: str):
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    out = IMAGES_DIR / name
    plt.savefig(out, dpi=160)
    print(f"Saved figure to: {out}")

def avg_kpi_bars(df: pd.DataFrame):
    """Bars: average report/enforcement/appeal-success rates by country."""
    kpis = df.groupby("country")[["report_rate","enforcement_rate","appeal_success_rate"]].mean().reset_index()
    # Report rate
    plt.figure(figsize=(7,5))
    plt.bar(kpis["country"], kpis["report_rate"])
    plt.title("Avg Report Rate by Country"); plt.xlabel("Country"); plt.ylabel("Rate")
    save_fig("exec_avg_report_rate.png"); plt.close()
    # Enforcement rate
    plt.figure(figsize=(7,5))
    plt.bar(kpis["country"], kpis["enforcement_rate"])
    plt.title("Avg Enforcement Rate by Country"); plt.xlabel("Country"); plt.ylabel("Rate")
    save_fig("exec_avg_enforcement_rate.png"); plt.close()
    # Appeal success rate
    plt.figure(figsize=(7,5))
    plt.bar(kpis["country"], kpis["appeal_success_rate"])
    plt.title("Avg Appeal Success Rate by Country"); plt.xlabel("Country"); plt.ylabel("Rate")
    save_fig("exec_avg_appeal_success.png"); plt.close()

def totals_reports_enforcements(df: pd.DataFrame):
    """Bars: total reports vs enforcements (6 months)."""
    totals = df.groupby("country")[["reports","enforcements"]].sum().reset_index()
    x = np.arange(len(totals)); w = 0.35
    plt.figure(figsize=(8,6))
    plt.bar(x, totals["reports"], width=w, label="Reports")
    plt.bar(x+w, totals["enforcements"], width=w, label="Enforcements")
    plt.xticks(x+w/2, totals["country"])
    plt.title("Total Reports vs Enforcements (6 months)")
    plt.xlabel("Country"); plt.ylabel("Count"); plt.legend()
    save_fig("exec_totals_reports_enforcements.png"); plt.close()

# -------- New with richer schema --------

def category_share_bars(df: pd.DataFrame, col="share_misinformation"):
    """
    Bars: average of a chosen category share by country.
    Call this multiple times for different categories if desired.
    """
    k = df.groupby("country")[col].mean().reset_index()
    plt.figure(figsize=(7,5))
    plt.bar(k["country"], k[col])
    plt.title(f"Avg {col} by Country"); plt.xlabel("Country"); plt.ylabel("Share of Reports")
    save_fig(f"exec_avg_{col}.png"); plt.close()

def source_share_bars(df: pd.DataFrame):
    """Bars: average report-source shares by country (one figure per source)."""
    for col in ["share_user","share_ai","share_trusted"]:
        k = df.groupby("country")[col].mean().reset_index()
        plt.figure(figsize=(7,5))
        plt.bar(k["country"], k[col])
        plt.title(f"Avg {col} by Country"); plt.xlabel("Country"); plt.ylabel("Share of Reports")
        save_fig(f"exec_avg_{col}.png"); plt.close()

def enforcement_mix_share_bars(df: pd.DataFrame):
    """
    Bars: enforcement-type shares by country.
    Computed from totals so denominator is enforcements.
    """
    totals = df.groupby("country")[["enf_removed","enf_warning","enf_suspension","enf_downrank","enforcements"]].sum().reset_index()
    for c in ["enf_removed","enf_warning","enf_suspension","enf_downrank"]:
        share = totals[c] / totals["enforcements"].where(totals["enforcements"] > 0, other=pd.NA)
        plt.figure(figsize=(7,5))
        plt.bar(totals["country"], share)
        plt.title(f"Enforcement Share — {c.replace('enf_','')}")
        plt.xlabel("Country"); plt.ylabel("Share of Enforcements")
        save_fig(f"exec_enforcement_share_{c}.png"); plt.close()

def misinfo_share_trend(df_roll: pd.DataFrame):
    """
    Line: trend of share_misinformation (7d rolling if present), averaged across countries.
    """
    col = "share_misinformation_roll7" if "share_misinformation_roll7" in df_roll.columns else "share_misinformation"
    daily = df_roll.groupby("date")[col].mean().reset_index()
    plt.figure(figsize=(12,6))
    plt.plot(daily["date"], daily[col], label=col)
    plt.title("Misinformation Share Trend (avg across countries)")
    plt.xlabel("Date"); plt.ylabel("Share of Reports"); plt.legend()
    save_fig("exec_misinfo_share_trend.png"); plt.close()
