from pathlib import Path
import numpy as np

# Paths
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
IMAGES_DIR = ROOT / "images"

# Reproducibility
SEED = 42
np.random.seed(SEED)

# Date range & countries
START_DATE = "2025-03-01"
END_DATE = "2025-08-31"
COUNTRIES = ["Singapore", "Indonesia", "Philippines", "Thailand", "Vietnam"]

# Base active users (approximate scale)
BASE_USERS = {
    "Singapore": 50000,
    "Indonesia": 400000,
    "Philippines": 200000,
    "Thailand": 150000,
    "Vietnam": 180000
}

# Injected patterns
SURGE_START = "2025-05-10"
SURGE_END = "2025-05-19"
RESPONSE_IMPROVE_PER_DAY = -0.02  # hours/day (global improvement)

COUNTRY_ADJUSTMENTS = {
    "Indonesia":  {"appeal_success": 1.15, "report_mult": 1.05},
    "Singapore":  {"appeal_success": 0.60, "report_mult": 0.95},
    "Philippines":{"appeal_success": 0.90, "report_mult": 1.00},
    "Thailand":   {"appeal_success": 0.85, "report_mult": 0.98},
    "Vietnam":    {"appeal_success": 0.95, "report_mult": 1.02},
}

# Output filenames
CSV_NAME = "tiktok_ts_apac_daily.csv"
KPIS_CSV = "country_kpis.csv"
ANOMALIES_CSV = "anomalies_reports_zscore_gt2.csv"
ML_REPORT = "ml_classification_report.txt"
