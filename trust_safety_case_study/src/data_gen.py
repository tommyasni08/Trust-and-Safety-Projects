import numpy as np
import pandas as pd
from datetime import timedelta
from config import (
    DATA_DIR, START_DATE, END_DATE, COUNTRIES, BASE_USERS,
    SURGE_START, SURGE_END, RESPONSE_IMPROVE_PER_DAY, COUNTRY_ADJUSTMENTS, CSV_NAME
)

# ----------------------------
# Category / Source / Enforcement design
# ----------------------------
VIOLATION_CATEGORIES = ["spam", "harassment_hate", "nudity", "misinformation", "child_safety", "other"]
BASE_CAT_P = np.array([0.40, 0.15, 0.12, 0.18, 0.02, 0.13])  # sums to 1

# Event window for misinformation (e.g., real-world news cycle)
MISINFO_EVENT_START = pd.Timestamp("2025-07-01")
MISINFO_EVENT_END   = pd.Timestamp("2025-07-10")

# Report source mixes by category (user, ai, trusted flaggers)
SOURCE_MIX = {
    "spam":             np.array([0.20, 0.75, 0.05]),
    "harassment_hate":  np.array([0.55, 0.25, 0.20]),
    "nudity":           np.array([0.30, 0.65, 0.05]),
    "misinformation":   np.array([0.65, 0.20, 0.15]),
    "child_safety":     np.array([0.25, 0.35, 0.40]),
    "other":            np.array([0.60, 0.30, 0.10]),
}

# Enforcement type mix by category (removal, warning, suspension, downrank)
ENF_MIX = {
    "spam":             np.array([0.60, 0.08, 0.02, 0.30]),
    "harassment_hate":  np.array([0.70, 0.15, 0.10, 0.05]),
    "nudity":           np.array([0.80, 0.10, 0.05, 0.05]),
    "misinformation":   np.array([0.30, 0.20, 0.00, 0.50]),
    "child_safety":     np.array([0.85, 0.00, 0.15, 0.00]),
    "other":            np.array([0.50, 0.25, 0.05, 0.20]),
}

# Overall enforcement rate baseline by category (fraction of reports enforced)
ENF_RATE_BY_CAT = {
    "spam":            (0.65, 0.85),
    "harassment_hate": (0.70, 0.90),
    "nudity":          (0.75, 0.95),
    "misinformation":  (0.45, 0.70),
    "child_safety":    (0.90, 0.99),
    "other":           (0.55, 0.75),
}

# Appeal success baseline by category (conditional on appeal)
APPEAL_SUCCESS_BY_CAT = {
    "spam":            (0.05, 0.12),
    "harassment_hate": (0.10, 0.25),
    "nudity":          (0.05, 0.10),
    "misinformation":  (0.18, 0.35),
    "child_safety":    (0.00, 0.02),
    "other":           (0.10, 0.20),
}

# Appeal likelihood given enforcement
APPEAL_RATE_BY_CAT = {
    "spam":            (0.03, 0.08),
    "harassment_hate": (0.06, 0.14),
    "nudity":          (0.04, 0.10),
    "misinformation":  (0.08, 0.18),
    "child_safety":    (0.01, 0.03),
    "other":           (0.05, 0.12),
}

def _adjust_category_mix(day: pd.Timestamp) -> np.ndarray:
    """Return P(category) adjusted for spam surge and misinfo event."""
    p = BASE_CAT_P.copy()
    surge_start = pd.to_datetime(SURGE_START)
    surge_end = pd.to_datetime(SURGE_END)
    if surge_start <= day <= surge_end:
        p[VIOLATION_CATEGORIES.index("spam")] *= 1.35
    if MISINFO_EVENT_START <= day <= MISINFO_EVENT_END:
        p[VIOLATION_CATEGORIES.index("misinformation")] *= 1.50
    p = p / p.sum()
    return p

def _multinomial_split(total: int, probs: np.ndarray) -> np.ndarray:
    if total <= 0:
        return np.zeros_like(probs, dtype=int)
    return np.random.multinomial(total, probs / probs.sum())

def generate_dataframe() -> pd.DataFrame:
    days = pd.date_range(start=START_DATE, end=END_DATE, freq="D")
    surge_start = pd.to_datetime(SURGE_START)
    surge_end = pd.to_datetime(SURGE_END)
    rows = []

    for day in days:
        # global response baseline with gradual improvement
        base_resp = 24 + RESPONSE_IMPROVE_PER_DAY * (day - days[0]).days
        base_resp = max(6, base_resp)
        cat_p = _adjust_category_mix(day)

        for c in COUNTRIES:
            users = BASE_USERS[c] + int(np.random.normal(0, BASE_USERS[c]*0.05))
            content_created = int(users * np.random.uniform(0.02, 0.05))

            # total reports baseline + multipliers
            report_rate = np.random.uniform(0.009, 0.015)
            mult = COUNTRY_ADJUSTMENTS[c]["report_mult"]
            if surge_start <= day <= surge_end:
                mult *= 1.8
            reports_total = int(content_created * report_rate * mult)
            reports_total = max(reports_total, 0)

            # split reports by category
            cat_counts = _multinomial_split(reports_total, cat_p)
            cat_map = dict(zip(VIOLATION_CATEGORIES, cat_counts))

            # aggregates to compute
            reports_user = reports_ai = reports_trusted = 0
            enf_removed = enf_warning = enf_suspension = enf_downrank = 0
            enforcements_total = 0
            appeals_total = 0
            successful_appeals_total = 0

            for cat, count in cat_map.items():
                if count == 0:
                    continue

                # source split
                src_mix = SOURCE_MIX[cat]
                src_counts = _multinomial_split(count, src_mix)
                reports_user += src_counts[0]
                reports_ai += src_counts[1]
                reports_trusted += src_counts[2]

                # enforcement rate draw (per category)
                enf_rate = np.random.uniform(*ENF_RATE_BY_CAT[cat])
                enfs = int(count * enf_rate)
                enforcements_total += enfs

                # enforcement types
                e_counts = _multinomial_split(enfs, ENF_MIX[cat])
                enf_removed     += e_counts[0]
                enf_warning     += e_counts[1]
                enf_suspension  += e_counts[2]
                enf_downrank    += e_counts[3]

                # appeals
                appeal_rate = np.random.uniform(*APPEAL_RATE_BY_CAT[cat])
                appeals = int(enfs * appeal_rate)

                # source adjustment: user reports ↑ appeal success; trusted ↓
                src_adj = 1.0
                if src_counts.sum() > 0:
                    share_user = src_counts[0] / src_counts.sum()
                    share_trust = src_counts[2] / src_counts.sum()
                    src_adj = np.clip(1.0 + 0.15*share_user - 0.10*share_trust, 0.5, 1.3)

                succ_rate = np.random.uniform(*APPEAL_SUCCESS_BY_CAT[cat]) * src_adj
                succ_rate = float(np.clip(succ_rate, 0.0, 1.0))
                succ = int(appeals * succ_rate)

                appeals_total += appeals
                successful_appeals_total += succ

            # response time
            response_time = round(np.random.uniform(base_resp-4, base_resp+4), 1)
            response_time = float(np.clip(response_time, 6, 36))

            rows.append([
                day, c, users, content_created, reports_total, enforcements_total,
                appeals_total, successful_appeals_total, response_time,
                # category counts
                cat_map.get("spam",0), cat_map.get("harassment_hate",0), cat_map.get("nudity",0),
                cat_map.get("misinformation",0), cat_map.get("child_safety",0), cat_map.get("other",0),
                # source counts
                reports_user, reports_ai, reports_trusted,
                # enforcement type counts
                enf_removed, enf_warning, enf_suspension, enf_downrank
            ])

    df = pd.DataFrame(rows, columns=[
        "date","country","active_users","content_created","reports","enforcements",
        "appeals","successful_appeals","median_response_time_hours",
        "reports_spam","reports_harassment_hate","reports_nudity","reports_misinformation",
        "reports_child_safety","reports_other",
        "reports_user","reports_ai","reports_trusted",
        "enf_removed","enf_warning","enf_suspension","enf_downrank"
    ])

    # Derived KPIs (overall)
    df["report_rate"] = df["reports"] / df["content_created"]
    df["enforcement_rate"] = df["enforcements"] / df["reports"].replace(0, np.nan)
    df["appeal_rate"] = df["appeals"] / df["enforcements"].replace(0, np.nan)
    df["appeal_success_rate"] = df["successful_appeals"] / df["appeals"].replace(0, np.nan)

    # Shares by category and source
    total_reports = df["reports"].replace(0, np.nan)
    for col in ["reports_spam","reports_harassment_hate","reports_nudity","reports_misinformation","reports_child_safety","reports_other"]:
        df[col.replace("reports_","share_")] = df[col] / total_reports
    for col in ["reports_user","reports_ai","reports_trusted"]:
        df[col.replace("reports_","share_")] = df[col] / total_reports

    return df

def save_csv(df: pd.DataFrame):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = DATA_DIR / CSV_NAME
    df.to_csv(out, index=False)
    return out

if __name__ == "__main__":
    df = generate_dataframe()
    path = save_csv(df)
    print(f"Saved dataset to: {path}")
