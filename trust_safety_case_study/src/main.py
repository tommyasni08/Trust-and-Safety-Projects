import pandas as pd
from config import DATA_DIR, CSV_NAME
from data_gen import generate_dataframe, save_csv
from quality_checks import run_checks
from kpis import add_rolling, save_country_kpis
from descriptive import (
    overall_summary,
    country_aggregates,
    country_category_totals,
    country_category_share_means,
    country_source_share_means,
    country_enforcement_totals,
    dominant_category_by_country,
)
from visuals_exploratory import (
    daily_reports_trend, enforcement_rate_box, appeal_success_box, response_time_trend,
    category_share_trend, source_share_trend
)
from visuals_executive import (
    avg_kpi_bars, totals_reports_enforcements,
    category_share_bars, source_share_bars, enforcement_mix_share_bars, misinfo_share_trend
)
from anomaly import save_anomalies

def run_all():
    # 1) Generate & save data
    df = generate_dataframe()
    csv_path = save_csv(df)
    print(f"[1/6] Dataset saved to: {csv_path}")

    # 2) Checks
    problems = run_checks(df)
    if problems:
        print("[WARN] QC issues:", problems)
    else:
        print("[2/6] QC passed")

    # 3) KPI engineering (rolling) & summaries
    #    Add rolling for mixes so visuals can show smoothed trends.
    df_roll = add_rolling(
        df,
        cols=("reports","enforcements","median_response_time_hours","share_misinformation","share_user"),
        window=7,
    )
    kpi_path = save_country_kpis(df)
    print(f"[3/6] Country KPI summary (wide) saved to: {kpi_path}")

    # 4) Descriptive outputs — save concise CSVs (no large console prints)
    desc_overall   = overall_summary(df)
    desc_country   = country_aggregates(df)
    cat_totals     = country_category_totals(df)
    cat_shares     = country_category_share_means(df)
    src_shares     = country_source_share_means(df)
    enf_totals     = country_enforcement_totals(df)
    dom_cat        = dominant_category_by_country(df)

    desc_overall.to_csv( DATA_DIR / "desc_overall_summary.csv"                 )
    desc_country.to_csv( DATA_DIR / "desc_country_aggregates.csv", index=False )
    cat_totals.to_csv(   DATA_DIR / "desc_category_totals.csv", index=False    )
    cat_shares.to_csv(   DATA_DIR / "desc_category_share_means.csv", index=False )
    src_shares.to_csv(   DATA_DIR / "desc_source_share_means.csv", index=False )
    enf_totals.to_csv(   DATA_DIR / "desc_enforcement_totals.csv", index=False )
    dom_cat.to_csv(      DATA_DIR / "desc_dominant_category_by_country.csv", index=False )
    print("[4/6] Descriptive CSVs saved to data/")

    # 5) Visualizations
    print("[5/6] Generating exploratory visuals...")
    daily_reports_trend(df)
    enforcement_rate_box(df)
    appeal_success_box(df)
    response_time_trend(df_roll)
    print("[5/6] Generating executive visuals...")
    avg_kpi_bars(df)
    totals_reports_enforcements(df)

    # 6) Anomalies (total reports, category/source shares)
    anomalies_path = save_anomalies(df, window=7, threshold=2.0)
    print(f"[6/6] Anomaly CSV and example plot saved. CSV: {anomalies_path}")

if __name__ == "__main__":
    run_all()
