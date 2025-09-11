import matplotlib.pyplot as plt
import pandas as pd
from config import IMAGES_DIR

def save_fig(name: str):
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    out = IMAGES_DIR / name
    plt.savefig(out, dpi=160)
    print(f"Saved figure to: {out}")

def daily_reports_trend(df: pd.DataFrame):
    """Line: daily reports by country."""
    plt.figure(figsize=(12,6))
    for c in df['country'].unique():
        s = df[df['country']==c]
        plt.plot(s['date'], s['reports'], label=c)
    plt.title("Daily Reports by Country")
    plt.xlabel("Date"); plt.ylabel("Reports"); plt.legend()
    save_fig("notebook_reports_trend.png"); plt.close()

def enforcement_rate_box(df: pd.DataFrame):
    """Box: enforcement rate distribution by country."""
    plt.figure(figsize=(8,5))
    data = [df[df['country']==c]['enforcement_rate'].dropna() for c in df['country'].unique()]
    plt.boxplot(data, labels=df['country'].unique())
    plt.title("Enforcement Rate Distribution by Country")
    plt.xlabel("Country"); plt.ylabel("Enforcement Rate")
    save_fig("enforcement_rate_box.png"); plt.close()

def appeal_success_box(df: pd.DataFrame):
    """Box: appeal success distribution by country."""
    plt.figure(figsize=(8,5))
    data = [df[df['country']==c]['appeal_success_rate'].dropna() for c in df['country'].unique()]
    plt.boxplot(data, labels=df['country'].unique())
    plt.title("Appeal Success Rate by Country (Distribution)")
    plt.xlabel("Country"); plt.ylabel("Appeal Success Rate")
    save_fig("appeal_success_box.png"); plt.close()

def response_time_trend(df_sorted: pd.DataFrame):
    """Line: response-time (7d rolling if present) by country."""
    plt.figure(figsize=(12,6))
    for c in df_sorted['country'].unique():
        s = df_sorted[df_sorted['country']==c]
        col = 'median_response_time_hours_roll7' if 'median_response_time_hours_roll7' in s else 'median_response_time_hours'
        plt.plot(s['date'], s[col], label=c)
    plt.title("Median Response Time (7d rolling) — by Country")
    plt.xlabel("Date"); plt.ylabel("Hours"); plt.legend()
    save_fig("response_time_trend.png"); plt.close()

# -------- New with richer schema --------

def category_share_trend(df_roll: pd.DataFrame, share_cols=("share_spam","share_misinformation")):
    """
    Line: selected category shares (7d rolling if provided) aggregated across countries (mean).
    """
    # If *_roll7 exists, use that instead
    cols = []
    for base in share_cols:
        roll = f"{base}_roll7"
        cols.append(roll if roll in df_roll.columns else base)

    daily = (df_roll.groupby("date")[cols].mean().reset_index())
    plt.figure(figsize=(12,6))
    for col in cols:
        plt.plot(daily["date"], daily[col], label=col)
    plt.title("Category Share Trend (avg across countries)")
    plt.xlabel("Date"); plt.ylabel("Share of Reports"); plt.legend()
    save_fig("expl_category_share_trend.png"); plt.close()

def source_share_trend(df_roll: pd.DataFrame, share_cols=("share_user","share_ai","share_trusted")):
    """
    Line: report-source shares over time (country-mean).
    """
    cols = []
    for base in share_cols:
        roll = f"{base}_roll7"
        cols.append(roll if roll in df_roll.columns else base)

    daily = (df_roll.groupby("date")[cols].mean().reset_index())
    plt.figure(figsize=(12,6))
    for col in cols:
        plt.plot(daily["date"], daily[col], label=col)
    plt.title("Report Source Share Trend (avg across countries)")
    plt.xlabel("Date"); plt.ylabel("Share of Reports"); plt.legend()
    save_fig("expl_source_share_trend.png"); plt.close()
