import pandas as pd
import numpy as np

def run_checks(df: pd.DataFrame, eps: float = 1e-6, share_tol: float = 0.02):
    """
    Validate integrity of the synthetic T&S dataset with category/source/enforcement extensions.

    Parameters
    ----------
    df : pd.DataFrame
        Dataset produced by src.data_gen.generate_dataframe()
    eps : float
        Numerical tolerance for equality checks (e.g., sums).
    share_tol : float
        Allowed deviation when checking that share columns sum to ~1.0.

    Returns
    -------
    problems : list[str]
        Human-readable list of issues found. Empty list means all checks passed.
    """
    problems: list[str] = []

    # --- 0) Required columns present
    required = [
        # core
        "date","country","active_users","content_created","reports","enforcements",
        "appeals","successful_appeals","median_response_time_hours",
        # categories
        "reports_spam","reports_harassment_hate","reports_nudity","reports_misinformation",
        "reports_child_safety","reports_other",
        # sources
        "reports_user","reports_ai","reports_trusted",
        # enforcement types
        "enf_removed","enf_warning","enf_suspension","enf_downrank",
        # kpis
        "report_rate","enforcement_rate","appeal_rate","appeal_success_rate",
        # shares (derived)
        "share_spam","share_harassment_hate","share_nudity","share_misinformation",
        "share_child_safety","share_other","share_user","share_ai","share_trusted",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        problems.append(f"Missing required columns: {missing}")

    if problems:
        return problems  # can't proceed with deeper checks

    # --- 1) Non-negativity for count columns
    count_cols_core = ["active_users","content_created","reports","enforcements","appeals","successful_appeals"]
    count_cols_cat  = ["reports_spam","reports_harassment_hate","reports_nudity","reports_misinformation","reports_child_safety","reports_other"]
    count_cols_src  = ["reports_user","reports_ai","reports_trusted"]
    count_cols_enf  = ["enf_removed","enf_warning","enf_suspension","enf_downrank"]

    nonneg_cols = count_cols_core + count_cols_cat + count_cols_src + count_cols_enf
    neg_mask = (df[nonneg_cols] < 0).any(axis=1)
    if neg_mask.any():
        problems.append(f"Negative counts found in {int(neg_mask.sum())} rows across one or more count columns.")

    # --- 2) Response time bounds
    rt_ok = df["median_response_time_hours"].between(0, 48)
    if not rt_ok.all():
        problems.append(f"Response times out of [0,48] hours in {int((~rt_ok).sum())} rows.")

    # --- 3) KPI rate bounds
    for col in ["report_rate","enforcement_rate","appeal_rate","appeal_success_rate"]:
        s = df[col].dropna()
        if not s.empty and not s.between(0, 1).all():
            problems.append(f"Rate out of bounds in {col} for {int((~s.between(0,1)).sum())} rows.")

    # --- 4) Logical inequalities
    gt_reports = (df["enforcements"] > df["reports"]).sum()
    if gt_reports:
        problems.append(f"'enforcements' exceed 'reports' in {gt_reports} rows.")

    gt_enf = (df["appeals"] > df["enforcements"]).sum()
    if gt_enf:
        problems.append(f"'appeals' exceed 'enforcements' in {gt_enf} rows.")

    gt_appeals = (df["successful_appeals"] > df["appeals"]).sum()
    if gt_appeals:
        problems.append(f"'successful_appeals' exceed 'appeals' in {gt_appeals} rows.")

    # --- 5) Conservation checks (sums match)
    # (a) categories sum to total reports
    cat_sum = df[count_cols_cat].sum(axis=1)
    cat_eq = np.isclose(cat_sum.values, df["reports"].values, atol=0, rtol=0)
    if (~cat_eq).any():
        problems.append(f"Category counts do not sum to 'reports' in {int((~cat_eq).sum())} rows.")

    # (b) sources sum to total reports
    src_sum = df[count_cols_src].sum(axis=1)
    src_eq = np.isclose(src_sum.values, df["reports"].values, atol=0, rtol=0)
    if (~src_eq).any():
        problems.append(f"Source counts do not sum to 'reports' in {int((~src_eq).sum())} rows.")

    # (c) enforcement-type counts sum to total enforcements
    enf_sum = df[count_cols_enf].sum(axis=1)
    enf_eq = np.isclose(enf_sum.values, df["enforcements"].values, atol=0, rtol=0)
    if (~enf_eq).any():
        problems.append(f"Enforcement-type counts do not sum to 'enforcements' in {int((~enf_eq).sum())} rows.")

    # --- 6) Share columns bounds and ~1.0 totals (only where reports > 0)
    share_cols_cat = ["share_spam","share_harassment_hate","share_nudity","share_misinformation","share_child_safety","share_other"]
    share_cols_src = ["share_user","share_ai","share_trusted"]

    # Bounds
    for col in share_cols_cat + share_cols_src:
        s = df[col].dropna()
        if not s.empty and not s.between(0 - eps, 1 + eps).all():
            problems.append(f"Share out of [0,1] in {col} for {int((~s.between(0 - eps, 1 + eps)).sum())} rows.")

    # Sum to ~1 when reports>0
    pos_report_mask = df["reports"] > 0
    if pos_report_mask.any():
        cat_share_sum = df.loc[pos_report_mask, share_cols_cat].sum(axis=1)
        src_share_sum = df.loc[pos_report_mask, share_cols_src].sum(axis=1)
        cat_ok = np.isclose(cat_share_sum.values, 1.0, atol=share_tol, rtol=0)
        src_ok = np.isclose(src_share_sum.values, 1.0, atol=share_tol, rtol=0)
        if (~cat_ok).any():
            problems.append(f"Category shares do not sum to ~1 within tolerance in {int((~cat_ok).sum())} rows.")
        if (~src_ok).any():
            problems.append(f"Source shares do not sum to ~1 within tolerance in {int((~src_ok).sum())} rows.")

    # --- 7) Date monotonicity within country (optional but nice)
    # Ensure there are no duplicate (country, date) pairs and dates are within the configured window
    dup_pairs = df.duplicated(subset=["country","date"]).sum()
    if dup_pairs:
        problems.append(f"Duplicate (country, date) pairs found: {int(dup_pairs)}")

    return problems
