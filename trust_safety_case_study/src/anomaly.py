import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from config import DATA_DIR, IMAGES_DIR

def detect_zscore_anomalies(series: pd.Series, window: int = 7, threshold: float = 2.0):
    """
    Rolling z-score anomaly detection.
    Returns DataFrame with z-scores and anomaly flag.
    """
    roll_mean = series.rolling(window, min_periods=1).mean()
    roll_std  = series.rolling(window, min_periods=1).std().replace(0, np.nan)
    zscores   = (series - roll_mean) / roll_std
    anomalies = (zscores.abs() > threshold)
    return pd.DataFrame({"value": series, "zscore": zscores, "anomaly": anomalies})

def detect_anomalies(df: pd.DataFrame, window: int = 7, threshold: float = 2.0) -> pd.DataFrame:
    """
    Detect anomalies across multiple metrics:
    - Total reports
    - Category shares: misinformation, child_safety
    - Source shares: user
    """
    results = []
    for c in df["country"].unique():
        s = df[df["country"]==c].sort_values("date")

        # Total reports
        res = detect_zscore_anomalies(s["reports"], window, threshold)
        res["country"] = c; res["date"] = s["date"].values
        res["metric"] = "reports"
        results.append(res)

        # Category shares
        for col in ["share_misinformation","share_child_safety"]:
            if col not in s.columns: continue
            res = detect_zscore_anomalies(s[col], window, threshold)
            res["country"] = c; res["date"] = s["date"].values
            res["metric"] = col
            results.append(res)

        # Source share (user reports)
        if "share_user" in s.columns:
            res = detect_zscore_anomalies(s["share_user"], window, threshold)
            res["country"] = c; res["date"] = s["date"].values
            res["metric"] = "share_user"
            results.append(res)

    out = pd.concat(results, ignore_index=True)
    return out

def save_anomalies(df: pd.DataFrame, window: int = 7, threshold: float = 2.0):
    """
    Run anomaly detection and save flagged rows to CSV + a couple of plots.
    """
    out = detect_anomalies(df, window, threshold)
    flagged = out[out["anomaly"]].copy()

    # Save CSV
    path = DATA_DIR / f"anomalies_window{window}_z{threshold}.csv"
    flagged.to_csv(path, index=False)
    print(f"Saved anomalies to: {path}")

    # Quick plot for total reports anomalies (example for first country)
    c0 = df["country"].unique()[0]
    s = df[df["country"]==c0].sort_values("date")
    res = out[(out["country"]==c0) & (out["metric"]=="reports")]

    plt.figure(figsize=(12,6))
    plt.plot(s["date"], s["reports"], label="Reports")
    plt.scatter(res["date"], res["value"], c=res["anomaly"].map({True:"red",False:"none"}), label="Anomaly", zorder=3)
    plt.title(f"Reports Anomalies — {c0}")
    plt.xlabel("Date"); plt.ylabel("Reports"); plt.legend()
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    fpath = IMAGES_DIR / f"anomalies_reports_{c0}.png"
    plt.savefig(fpath, dpi=160); plt.close()
    print(f"Saved anomaly plot to: {fpath}")

    return path
