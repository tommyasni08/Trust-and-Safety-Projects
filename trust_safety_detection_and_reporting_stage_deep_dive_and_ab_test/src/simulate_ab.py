"""
simulate_ab.py — Synthetic A/B test dataset generator for Trust & Safety triage experiments.

This script creates a synthetic dataset representing moderation "cases" and assigns
them to either Arm A (baseline) or Arm B (treatment).

Each case has:
  - Inputs: country, category, AI score (Beta-distributed by category)
  - Policy: threshold_used, category weight, priority_score
  - Outcomes: queued?, enforced?, appeal_success?
  - Latency: timestamps for triage and enqueue

The function simulate_cases(cfg) implements the logic step-by-step:
  1. Sample countries & categories
  2. Generate AI scores by category (Beta distributions)
  3. Create latent "true violation" label from base prevalence + AI score
  4. Randomize cases into experiment arms (A or B)
  5. Compute priority score, apply threshold & cutoff → decide queueing
  6. Simulate latency (triage → enqueue)
  7. Simulate enforcement outcome (precision proxy)
  8. Simulate appeals (false positive proxy)
  9. Return a tidy DataFrame

"""


import numpy as np
import pandas as pd
from datetime import datetime
from numpy.random import default_rng
from scipy.stats import beta
# --- Configuration with all knobs (seed, thresholds, weights, latency, etc.)
from config import SimConfig

def simulate_cases(cfg: SimConfig) -> pd.DataFrame:
    """
    Generate one row per case with randomized assignment to arm (A/B) and
    simulated outcomes. Returns a pandas.DataFrame suitable for KPI/AB analysis.

    Parameters
    ----------
    cfg : SimConfig
        Holds all tunable parameters (category weights, thresholds, latency, etc.).
    """
    # RNG with a fixed seed → reproducible runs
    rng = default_rng(cfg.seed)

    # Total number of cases to simulate
    n = cfg.n_cases

    # Sample a country for each case using configured probabilities
    countries = rng.choice(cfg.countries, size=n, p=[0.2,0.25,0.2,0.2,0.15])

    # Sample a content category for each case (spam, child_safety, etc.)
    categories = rng.choice(cfg.categories, size=n, p=[0.1,0.1,0.2,0.3,0.2,0.1])

    # --- AI scores ---
    # Draw AI confidence for each case from a per-category Beta(α,β).
    # This makes severe categories skew higher and noisy categories skew lower.
    ai_scores = np.zeros(n)
    for i, cat in enumerate(categories):
        a, b = cfg.ai_beta_params[cat]
        ai_scores[i] = beta(a, b).rvs(random_state=rng)

    # Latent "true violation" probability blends:
    #   - base prevalence for the category (prior)
    #   - the AI score (evidence)
    base_probs = np.array([cfg.base_true_violation[c] for c in categories])
    truth_prob = np.clip(base_probs*0.6 + 0.4*ai_scores, 0, 1)
    true_violation = rng.binomial(1, truth_prob)

    # Randomize the experiment arm at the case level (unit = case_id)
    arm = rng.choice(["A","B"], size=n)

    # --- Triage policy: priority & queue decision ---
    # We blend model confidence (ai_score) and policy severity (category weight) into a
    # single priority score, then apply TWO gates:
    #   1) correctness  gate: ai_score ≥ threshold_used
    #   2) importance   gate: priority_score ≥ priority_cutoff
    # A case is queued only if it passes both gates.
    priority = np.zeros(n)
    threshold_used = np.zeros(n)
    queued = np.zeros(n, dtype=int)
    for i in range(n):
        wc = cfg.weights_A if arm[i]=="A" else cfg.weights_B
        # Additive priority: policy severity + scaled AI confidence
        prio = wc[categories[i]] + cfg.w_ai*ai_scores[i]
        priority[i] = prio

        # Arm-specific AI threshold (B usually lower to increase recall)
        th = cfg.threshold_A if arm[i]=="A" else cfg.threshold_B
        threshold_used[i] = th

        # Two-gate triage: require BOTH confidence and importance
        queued[i] = int(ai_scores[i] >= th and prio >= cfg.priority_cutoff)

    # --- Latency timestamps ---
    # We simulate time between triage and enqueue to compute p50/p90 latency later.
    # Arm B may be faster/slower depending on config to illustrate trade-offs.
    now = datetime(2025,7,1,12,0,0)
    lat_sec = np.where(
        arm=="A",
        np.random.exponential(cfg.latency_mean_sec_A, size=n),
        np.random.exponential(cfg.latency_mean_sec_B, size=n)
    )
    ts_triage = np.array([now]*n, dtype="datetime64[s]")
    ts_enqueued = ts_triage + lat_sec.astype("timedelta64[s]")
    ts_enqueued = np.where(queued==1, ts_enqueued, np.datetime64("NaT"))

    # --- Enforcement (proxy for precision) ---
    # After a case is queued, we simulate whether it results in enforcement.
    # Enforcement probability increases with ai_score, true_violation, and category strictness.
    enforced = np.zeros(n, dtype=int)
    for i in range(n):
        if queued[i]==1:
            base_strength = cfg.enforce_strength[categories[i]]
            enforce_prob = np.clip(0.3*ai_scores[i] + 0.5*true_violation[i] + base_strength, 0, 0.99)
            enforced[i] = rng.binomial(1, enforce_prob)
        else:
            enforced[i] = 0

    # --- Appeals (proxy for false positives) ---
    # If enforced, an appeal may succeed. Borderline cases near the threshold are more
    # likely to be overturned; severe categories almost never.
    appeal_success = np.zeros(n, dtype=int)
    for i in range(n):
        if enforced[i]==1:
            base_app = cfg.appeal_success_base[categories[i]]
            borderline = (ai_scores[i]-threshold_used[i])<0.08
            appeal_prob = np.clip(base_app + 0.05*borderline, 0, 0.9)
            appeal_success[i] = rng.binomial(1, appeal_prob)
        else:
            appeal_success[i] = 0

    # Assemble DataFrame
    df = pd.DataFrame({
        "case_id": np.arange(1, n+1),
        "arm": arm,
        "country": countries,
        "category": categories,
        "ai_score": ai_scores.round(4),
        "true_violation": true_violation,
        "priority_score": priority.round(2),
        "threshold_used": threshold_used,
        "queued": queued,
        "enforced": enforced,
        "appeal_success": appeal_success,
        "ts_triage": ts_triage,
        "ts_enqueued": ts_enqueued
    })
    return df

def main():
    cfg = SimConfig()
    df = simulate_cases(cfg)
    out = "../data/abtest_synthetic.csv"
    df.to_csv(out, index=False)
    print(f"Saved {len(df):,} cases to {out}")
    print(df.head(5))

if __name__ == "__main__":
    main()
