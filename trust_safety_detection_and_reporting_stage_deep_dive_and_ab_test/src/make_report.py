
import os, base64, datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(BASE, "data/abtest_synthetic.csv")
IMG_DIR = os.path.join(BASE, "images")
REPORT_DIR = os.path.join(BASE, "reports")
os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

def ensure_data():
    try:
        from .simulate_ab import main as sim_main
        sim_main()
    except Exception as e:
        print("Simulator failed, attempting inline fallback...", e)
        import numpy as np, pandas as pd
        from numpy.random import default_rng
        rng = default_rng(7); n=5000
        countries = rng.choice(["SG","ID","PH","TH","VN"], size=n, replace=True, p=[0.15,0.35,0.18,0.16,0.16])
        categories = rng.choice(["child_safety","hate","misinformation","spam","nudity","other"], size=n, replace=True, p=[0.05,0.10,0.20,0.40,0.15,0.10])
        bp = {"child_safety": (5,2), "hate": (4,2), "misinformation": (3,3), "spam": (3,4), "nudity": (4,3), "other": (2,5)}
        ai_scores = np.array([np.random.beta(*bp[c]) for c in categories])
        base_prev = {"child_safety":0.80,"hate":0.60,"misinformation":0.35,"spam":0.30,"nudity":0.50,"other":0.10}
        tv = np.array([base_prev[c] for c in categories])
        truth_prob = np.clip(tv*0.6 + 0.4*ai_scores, 0, 1)
        true_violation = np.random.binomial(1, truth_prob)
        arm = np.random.choice(["A","B"], size=n)
        weights_A = {"child_safety":30,"hate":25,"misinformation":15,"spam":10,"nudity":12,"other":5}
        weights_B = {"child_safety":40,"hate":32,"misinformation":15,"spam":10,"nudity":12,"other":5}
        w_ai=60; cutoff=50; thr_A=0.70; thr_B=0.60
        priority=[]; queued=[]; thr_used=[]
        for i in range(n):
            wc = weights_A if arm[i]=="A" else weights_B
            prio = wc[categories[i]] + w_ai*ai_scores[i]
            priority.append(prio)
            th = thr_A if arm[i]=="A" else thr_B
            thr_used.append(th)
            queued.append(int(ai_scores[i]>=th and prio>=cutoff))
        priority = np.round(priority,2)
        now = np.datetime64("2025-07-01T12:00:00")
        lat_A = np.random.exponential(8*3600, size=n)
        lat_B = np.random.exponential(7.5*3600, size=n)
        lat = np.where(arm=="A", lat_A, lat_B).astype("timedelta64[s]")
        ts_triage = np.array([now]*n, dtype="datetime64[s]")
        ts_enq = ts_triage + lat
        ts_enq = np.where(np.array(queued)==1, ts_enq, np.datetime64("NaT"))
        enforce_strength={"child_safety":0.30,"hate":0.20,"misinformation":0.05,"spam":0.00,"nudity":0.10,"other":-0.10}
        enf_prob = np.clip(0.3*ai_scores + 0.5*true_violation + np.array([enforce_strength[c] for c in categories]), 0, 0.99)
        enforced = np.where(np.array(queued)==1, np.random.binomial(1, enf_prob), 0)
        appeal_base={"child_safety":0.00,"hate":0.05,"misinformation":0.12,"spam":0.15,"nudity":0.10,"other":0.20}
        thr_used_arr = np.array(thr_used)
        borderline = (ai_scores - thr_used_arr) < 0.08
        appeal_prob = np.clip(np.array([appeal_base[c] for c in categories]) + 0.05*borderline, 0, 0.9)
        appeal_success = np.where(enforced==1, np.random.binomial(1, appeal_prob), 0)
        df = pd.DataFrame({
            "case_id": np.arange(1, n+1),
            "arm": arm,
            "country": countries,
            "category": categories,
            "ai_score": np.round(ai_scores,4),
            "true_violation": true_violation,
            "priority_score": priority,
            "threshold_used": thr_used_arr,
            "queued": queued,
            "enforced": enforced,
            "appeal_success": appeal_success,
            "ts_triage": ts_triage,
            "ts_enqueued": ts_enq
        })
        out = os.path.join(BASE, "data/abtest_synthetic.csv")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        df.to_csv(out, index=False)
        print("Inline synthetic dataset written →", out)

def build_report():
    ensure_data()
    df = pd.read_csv(DATA)

    severe = df["category"].isin(["child_safety","hate"])
    sev = df.loc[severe]
    severe_capture = sev.groupby("arm")["queued"].mean()
    precision = df[df["queued"]==1].groupby("arm")["enforced"].mean()
    queue_rate = df.groupby("arm")["queued"].mean()

    q = df[df["queued"]==1].copy()
    q["latency_sec"] = (pd.to_datetime(q["ts_enqueued"]) - pd.to_datetime(q["ts_triage"])).dt.total_seconds()
    latency_p50 = q.groupby("arm")["latency_sec"].median()
    latency_p90 = q.groupby("arm")["latency_sec"].quantile(0.90)
    appeal_rate = df[df["enforced"]==1].groupby("arm")["appeal_success"].mean()

    sev_counts = sev.groupby("arm")["queued"].agg(["sum","count"]).reindex(["A","B"])
    z_sev = sm.stats.proportions_ztest(sev_counts["sum"], sev_counts["count"])

    prec_counts = q.groupby("arm")["enforced"].agg(["sum","count"]).reindex(["A","B"])
    z_prec = sm.stats.proportions_ztest(prec_counts["sum"], prec_counts["count"])

    q = q.copy()
    q["arm_B"] = (q["arm"]=="B").astype(int)
    logit = smf.logit("enforced ~ arm_B + C(country) + C(category)", data=q).fit(disp=False)

    latA = q[q["arm"]=="A"]["latency_sec"].dropna()
    latB = q[q["arm"]=="B"]["latency_sec"].dropna()
    mw = stats.mannwhitneyu(latA, latB, alternative="two-sided")

    fig, ax = plt.subplots(figsize=(8,5))
    arms = ["A","B"]; x = np.arange(len(arms)); width = 0.2
    vals1 = [severe_capture.get(a, np.nan) for a in arms]
    vals2 = [precision.get(a, np.nan) for a in arms]
    vals3 = [queue_rate.get(a, np.nan) for a in arms]
    ax.bar(x - width, vals1, width, label="Severe capture")
    ax.bar(x,         vals2, width, label="Precision")
    ax.bar(x + width, vals3, width, label="Queue rate")
    ax.set_xticks(x); ax.set_xticklabels(arms)
    ax.set_ylim(0,1); ax.set_ylabel("Rate"); ax.set_title("A/B Summary KPIs"); ax.legend()
    plt.tight_layout()
    chart_path = os.path.join(IMG_DIR, "abtest_metrics.png"); plt.savefig(chart_path, dpi=200); plt.close()

    with open(chart_path, "rb") as f:
        chart_b64 = base64.b64encode(f.read()).decode()

    template = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<title>T&S A/B Test Report</title>
<style>
body {{ font-family: Arial, Helvetica, sans-serif; margin: 32px; color: #0f172a; }}
h1, h2, h3 {{ margin-top: 24px; }}
.header {{ display:flex; justify-content: space-between; align-items: baseline; }}
.tag {{ background:#eef2ff; padding:4px 8px; border-radius:6px; font-size:12px; color:#3730a3; }}
.tbl {{ border-collapse: collapse; margin: 8px 0 24px 0; }}
.tbl th, .tbl td {{ border-bottom: 1px solid #e5e7eb; padding: 8px 10px; text-align: left; }}
.note {{ color:#475569; font-size: 13px; }}
.kpi-grid {{ display:grid; grid-template-columns: repeat(2, minmax(260px, 1fr)); gap: 18px; }}
.card {{ border:1px solid #e5e7eb; border-radius:10px; padding:14px; }}
.code {{ background:#f8fafc; padding:8px 10px; border-radius:8px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
footer {{ margin-top: 28px; color:#64748b; font-size:12px; }}
</style>
</head>
<body>
<div class="header">
  <h1>Trust & Safety A/B Test — Results</h1>
  <span class="tag">Synthetic simulation</span>
</div>
<p class="note">Report generated __NOW__. Unit: <b>case_id</b>. Arms: <b>A</b> (baseline) vs <b>B</b> (lower threshold + severe weights).</p>

<h2>Summary Chart</h2>
<img src="data:image/png;base64,__CHART__" alt="A/B Summary KPIs" style="max-width:720px;border:1px solid #e5e7eb;border-radius:10px;padding:6px;">

<h2>KPIs by Arm</h2>
<table class="tbl">
  <tr><th>Metric</th><th>Arm A</th><th>Arm B</th></tr>
  <tr><td>Severe-case capture</td><td>__SEV_A__</td><td>__SEV_B__</td></tr>
  <tr><td>Precision proxy</td><td>__PREC_A__</td><td>__PREC_B__</td></tr>
  <tr><td>Queue rate</td><td>__Q_A__</td><td>__Q_B__</td></tr>
  <tr><td>Latency p50 (sec)</td><td>__L50_A__</td><td>__L50_B__</td></tr>
  <tr><td>Latency p90 (sec)</td><td>__L90_A__</td><td>__L90_B__</td></tr>
  <tr><td>Appeal success</td><td>__APP_A__</td><td>__APP_B__</td></tr>
</table>

<h2>Statistical Tests</h2>
<div class="card">
  <h3>Proportion tests (two-sample z-test)</h3>
  <p class="code">Severe capture: z = __ZSEV__, p = __PSEV__<br/>
  Precision: z = __ZPREC__, p = __PPREC__</p>
</div>

<div class="card">
  <h3>Logistic regression (queued only)</h3>
  <pre class="code">__LOGIT__</pre>
</div>

<div class="card">
  <h3>Mann–Whitney U (latency, queued only)</h3>
  <p class="code">U = __U__, p = __PU__</p>
  <p class="note">Non-parametric test comparing latency distributions (robust to outliers and skew).</p>
</div>

<footer>
This report is generated from synthetic data and is intended for demonstration of experiment design and analysis workflows in Trust & Safety.
</footer>
</body>
</html>
"""

    def pct(x): return f"{x*100:.2f}%"
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    logit_txt = logit.summary2().as_text()

    html = (template
            .replace("__NOW__", now)
            .replace("__CHART__", chart_b64)
            .replace("__SEV_A__", pct(severe_capture.get("A", float("nan"))))
            .replace("__SEV_B__", pct(severe_capture.get("B", float("nan"))))
            .replace("__PREC_A__", pct(precision.get("A", float("nan"))))
            .replace("__PREC_B__", pct(precision.get("B", float("nan"))))
            .replace("__Q_A__", pct(queue_rate.get("A", float("nan"))))
            .replace("__Q_B__", pct(queue_rate.get("B", float("nan"))))
            .replace("__L50_A__", f"{latency_p50.get('A', float('nan')):.1f}")
            .replace("__L50_B__", f"{latency_p50.get('B', float('nan')):.1f}")
            .replace("__L90_A__", f"{latency_p90.get('A', float('nan')):.1f}")
            .replace("__L90_B__", f"{latency_p90.get('B', float('nan')):.1f}")
            .replace("__APP_A__", pct(appeal_rate.get('A', float('nan'))))
            .replace("__APP_B__", pct(appeal_rate.get('B', float('nan'))))
            .replace("__ZSEV__", f"{z_sev[0]:.2f}")
            .replace("__PSEV__", f"{z_sev[1]:.6f}")
            .replace("__ZPREC__", f"{z_prec[0]:.2f}")
            .replace("__PPREC__", f"{z_prec[1]:.6f}")
            .replace("__LOGIT__", logit_txt)
            .replace("__U__", f"{mw.statistic:.0f}")
            .replace("__PU__", f"{mw.pvalue:.6f}")
           )

    out_html = os.path.join(REPORT_DIR, "abtest_report.html")
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html)
    print("Report written →", out_html)
    print("Chart written →", os.path.join(IMG_DIR, "abtest_metrics.png"))

if __name__ == "__main__":
    build_report()
