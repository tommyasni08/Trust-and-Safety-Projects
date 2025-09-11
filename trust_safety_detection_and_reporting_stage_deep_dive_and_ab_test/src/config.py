from dataclasses import dataclass, field

@dataclass
class SimConfig:
    seed: int = 7
    n_cases: int = 5000

    countries: tuple = ("SG","ID","PH","TH","VN")
    categories: tuple = ("child_safety","hate","misinformation","spam","nudity","other")

    base_true_violation: dict = field(default_factory=lambda: {
        "child_safety": 0.80,
        "hate": 0.60,
        "misinformation": 0.35,
        "spam": 0.30,
        "nudity": 0.50,
        "other": 0.10,
    })

    ai_beta_params: dict = field(default_factory=lambda: {
        "child_safety": (5,2),
        "hate": (4,2),
        "misinformation": (3,3),
        "spam": (3,4),
        "nudity": (4,3),
        "other": (2,5),
    })

    threshold_A: float = 0.70
    threshold_B: float = 0.60

    weights_A: dict = field(default_factory=lambda: {
        "child_safety": 30,
        "hate": 25,
        "misinformation": 15,
        "spam": 10,
        "nudity": 12,
        "other": 5,
    })
    weights_B: dict = field(default_factory=lambda: {
        "child_safety": 40,
        "hate": 32,
        "misinformation": 15,
        "spam": 10,
        "nudity": 12,
        "other": 5,
    })

    w_ai: int = 60
    priority_cutoff: int = 50

    latency_mean_sec_A: float = 8 * 3600
    latency_mean_sec_B: float = 7.5 * 3600

    enforce_strength: dict = field(default_factory=lambda: {
        "child_safety": 0.30,
        "hate": 0.20,
        "misinformation": 0.05,
        "spam": 0.00,
        "nudity": 0.10,
        "other": -0.10,
    })

    appeal_success_base: dict = field(default_factory=lambda: {
        "child_safety": 0.00,
        "hate": 0.05,
        "misinformation": 0.12,
        "spam": 0.15,
        "nudity": 0.10,
        "other": 0.20,
    })
