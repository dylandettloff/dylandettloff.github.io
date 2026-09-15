# Extracted from Dylan Dettloff's research notebook. See README for provenance.
# Standard library imports for text parsing and file access.
import re
from pathlib import Path

# Core numerical and tabular tools used throughout the model.
import numpy as np
import pandas as pd

# Dataclass keeps community inputs explicit and easy to validate.
from dataclasses import dataclass
from typing import Dict, Tuple, Optional, Callable, List

# Technology input table.
# This is the technology knowledge base for the model.
# Each row stores broad ranges or qualitative labels taken from literature,
# vendor information, or expert judgment. The Monte Carlo simulation later
# samples from these ranges to represent uncertainty instead of pretending we
# know a single exact value for each technology.
TECH_DATA = {
    "RO": {
        "Recovery Ratio": "40-75%",
        "Reliability": "Moderate",
        "Complexity": "High",
        "SEC (kWh/m³)": "0.14-0.24",
        "OPEX ($/m³)": "$0.60-1.50",
        "CAPEX ($/m³-d)": "$250-300",
        "Carbon (kg/m³)": "1.7-2.8",
        "Brine Ratio": "25-60%",
        "Cleaning Freq.": "6-12 Months",
        "Start-Stop": "Limited",
    },
    "ED": {
        "Recovery Ratio": "80-90%",
        "Reliability": "Moderate",
        "Complexity": "Moderate",
        "SEC (kWh/m³)": "0.3-1.5",
        "OPEX ($/m³)": "$0.50-2.50",
        "CAPEX ($/m³-d)": "$1000-2500",
        "Carbon (kg/m³)": "Minimal",
        "Brine Ratio": "10-20%",
        "Cleaning Freq.": "6 Months",
        "Start-Stop": "Very High",
    },
    "HDH": {
        "Recovery Ratio": "30-45%",
        "Reliability": "High",
        "Complexity": "Low",
        "SEC (kWh/m³)": "~0 (Thermal)",
        "OPEX ($/m³)": "$0.39-0.66",
        "CAPEX ($/m³-d)": "$500-3000",
        "Carbon (kg/m³)": "None",
        "Brine Ratio": "Minimal",
        "Cleaning Freq.": "1-3 Months",
        "Start-Stop": "High",
    },
    "MSPD": {
        "Recovery Ratio": "60-100%",
        "Reliability": "Very High",
        "Complexity": "Very Low",
        "SEC (kWh/m³)": "~0 (Thermal)",
        "OPEX ($/m³)": "~$2.72",
        "CAPEX ($/m³-d)": "Variable",
        "Carbon (kg/m³)": "None",
        "Brine Ratio": "No Brine",
        "Cleaning Freq.": "Minimal",
        "Start-Stop": "Passive",
    },
}

# Transferable community schema.
# The point of this block is to make the model reusable for any location.
# Instead of hand-writing custom logic for each community, we define one
# standard input template and derive ranking weights from those inputs.
# That means a new community can usually be added by editing the CSV only.
BIN_NAMES = ["Technical", "Operations", "Environmental", "Cost"]
BIN_INDEX = {name: i for i, name in enumerate(BIN_NAMES)}
DEFAULT_BIN_WEIGHTS = np.array([0.25, 0.25, 0.25, 0.25])

@dataclass(frozen=True)
class CommunityProfile:
    """Standardized community inputs used to derive MCDA priorities.

    All 1-5 ratings follow the same convention:
    1 = low importance / low stress / high capacity
    5 = high importance / high stress / low capacity

    The model converts these ratings into bin weights automatically, so the
    same input template can be reused for any new community.
    """
    salinity_type: str
    water_quality_risk: int = 3
    energy_stress: int = 3
    environmental_sensitivity: int = 3
    cost_sensitivity: int = 3
    operator_capacity: int = 3
    growth_pressure: int = 3
    weight_flexibility: float = 0.15
    minimum_bin_weight: float = 0.10
    maximum_bin_weight: float = 0.75
    notes: str = ""

COMMUNITY_TEMPLATE_COLUMNS = [
    "community",
    "salinity_type",
    "water_quality_risk",
    "energy_stress",
    "environmental_sensitivity",
    "cost_sensitivity",
    "operator_capacity",
    "growth_pressure",
    "weight_flexibility",
    "notes",
]
# Allowed source-water classes used by the initial technology screen.
VALID_SALINITY_TYPES = {"seawater", "brackish", "mixed"}

# Default CSV location. This file is intended to be the source of truth for
# the communities you want to analyze in the notebook.
DEFAULT_COMMUNITY_INPUT_CSV = Path(__file__).with_name("community_inputs.csv")

def bounded_rating(value, default=3) -> int:
    """Clamp community ratings to the expected 1-5 range.

    This prevents accidental out-of-range values in the CSV from creating
    extreme weights later in the pipeline.
    """
    if value is None or pd.isna(value):
        return default
    return int(np.clip(int(value), 1, 5))

def coerce_float(value, default) -> float:
    """Convert optional numeric CSV inputs safely to float."""
    if value is None or pd.isna(value):
        return default
    return float(value)

def validate_community_input_table(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize a CSV/DataFrame before running the model.

    This function is intentionally strict because community inputs drive the
    entire ranking process. Catching bad column names or invalid salinity tags
    up front is much easier than debugging strange ranking outputs later.
    """
    missing = [col for col in COMMUNITY_TEMPLATE_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required community columns: {missing}")

    clean = df[COMMUNITY_TEMPLATE_COLUMNS].copy()
    clean["community"] = clean["community"].astype(str).str.strip()
    clean["salinity_type"] = clean["salinity_type"].astype(str).str.strip().str.lower()

    if clean["community"].duplicated().any():
        dups = clean.loc[clean["community"].duplicated(), "community"].tolist()
        raise ValueError(f"Community names must be unique. Duplicates: {dups}")

    invalid_salinity = sorted(set(clean.loc[~clean["salinity_type"].isin(VALID_SALINITY_TYPES), "salinity_type"]))
    if invalid_salinity:
        raise ValueError(
            f"Invalid salinity_type values: {invalid_salinity}. Expected one of {sorted(VALID_SALINITY_TYPES)}"
        )

    return clean

def load_community_input_source(source) -> pd.DataFrame:
    """Load community inputs from a CSV path or an in-memory DataFrame.

    Supporting both file paths and DataFrames makes the model easy to use
    both in notebooks and in future scripts or apps.
    """
    if isinstance(source, pd.DataFrame):
        return validate_community_input_table(source)
    if isinstance(source, (str, Path)):
        csv_path = Path(source)
        return validate_community_input_table(pd.read_csv(csv_path))
    raise TypeError("source must be a pandas DataFrame or a CSV file path")

def load_communities_from_table(df: pd.DataFrame) -> Dict[str, CommunityProfile]:
    """Build community profiles from a standard tabular template.

    This is the main transfer interface for the model. You can replace the
    example rows with any set of communities as long as the columns match
    COMMUNITY_TEMPLATE_COLUMNS.
    """
    # Convert each CSV row into a strongly-typed CommunityProfile so later
    # functions can assume the inputs are clean and complete.
    communities = {}
    for row in df.to_dict(orient="records"):
        communities[row["community"]] = CommunityProfile(
            salinity_type=str(row["salinity_type"]),
            water_quality_risk=bounded_rating(row.get("water_quality_risk"), 3),
            energy_stress=bounded_rating(row.get("energy_stress"), 3),
            environmental_sensitivity=bounded_rating(row.get("environmental_sensitivity"), 3),
            cost_sensitivity=bounded_rating(row.get("cost_sensitivity"), 3),
            operator_capacity=bounded_rating(row.get("operator_capacity"), 3),
            growth_pressure=bounded_rating(row.get("growth_pressure"), 3),
            weight_flexibility=coerce_float(row.get("weight_flexibility"), 0.15),
            notes=str(row.get("notes", "")),
        )
    return communities

def load_communities(source) -> Dict[str, CommunityProfile]:
    """Convenience wrapper for loading validated community profiles from CSV."""
    return load_communities_from_table(load_community_input_source(source))

# The CSV is the source of truth for community inputs.
# Edit community_inputs.csv to add, remove, or update communities without
# changing notebook code. The rest of the model reads from these variables,
# so loading the CSV here keeps everything downstream generic.
COMMUNITY_INPUT_TABLE = load_community_input_source(DEFAULT_COMMUNITY_INPUT_CSV)
COMMUNITIES = load_communities_from_table(COMMUNITY_INPUT_TABLE)

TECH_COMPAT = {
    "RO": {"seawater", "brackish", "mixed"},
    "ED": {"brackish", "mixed"},
    "HDH": {"seawater", "mixed"},
    "MSPD": {"seawater", "mixed"},
}

# These parser helpers translate human-readable spreadsheet-style entries
# into numeric values the model can sample and score.
def parse_range(s: str):
    # Example: "$250-300" -> (250.0, 300.0)
    s0 = s.replace(",", "").replace("$", "").replace("%", "").replace("~", "").strip()
    m = re.search(r"(\d+(\.\d+)?)\s*[-–]\s*(\d+(\.\d+)?)", s0)
    if not m:
        return None
    return float(m.group(1)), float(m.group(3))

def parse_number(s: str):
    # Example: "~$2.72" -> 2.72
    s0 = s.replace(",", "").replace("$", "").replace("%", "").strip()
    m = re.search(r"(\d+(\.\d+)?)", s0)
    return float(m.group(1)) if m else None

def sample_from_cell(cell: str, rng: np.random.Generator):
    """
    Convert a cell to a sampled numeric value.
    - If range -> sample uniform across range.
    - If single number -> that number.
    - If qualitative/none -> None (handled elsewhere).

    This is one of the main uncertainty hooks in the model. Every time the
    simulation runs, it can draw a different value from the provided range.
    """
    r = parse_range(cell)
    if r:
        return rng.uniform(r[0], r[1])
    n = parse_number(cell)
    return n

# These functions convert raw technology parameters into comparable economic
# and environmental outputs before MCDA scoring happens.
def capital_recovery_factor(discount_rate: float, lifetime_years: int) -> float:
    # CRF is the standard engineering-economics formula for spreading capital
    # cost across the life of an asset.
    r = discount_rate
    n = lifetime_years
    if r <= 0:
        return 1.0 / n
    return (r * (1 + r) ** n) / ((1 + r) ** n - 1)

def annualized_capex_per_m3(capex_per_m3_day: float, crf: float, utilization: float) -> float:
    # CAPEX is provided as dollars per unit of installed daily capacity.
    # We convert that into dollars per cubic meter of produced water so it can
    # be combined with OPEX in LCOW.
    return capex_per_m3_day * crf / (365.0 * utilization)

def infer_non_energy_opex(opex_total: float, sec_kwh_m3: float, baseline_elec_price: float) -> float:
    # Split total OPEX into an energy-driven part and a residual non-energy
    # part so future electricity-price scenarios can affect only the part that
    # should actually move with energy.
    non_energy = opex_total - (sec_kwh_m3 * baseline_elec_price)
    return max(non_energy, 0.0)

def compute_lcow(capex_per_m3_day: float | None,
                 opex_total: float,
                 sec_kwh_m3: float | None,
                 elec_price: float,
                 baseline_elec_price: float,
                 discount_rate: float,
                 lifetime_years: int,
                 utilization: float) -> float:
    # LCOW is the model's simplified unit-cost estimate for comparing options.
    crf = capital_recovery_factor(discount_rate, lifetime_years)

    # If SEC is unknown (thermal placeholder), we assume energy cost is embedded in OPEX_total.
    if sec_kwh_m3 is None:
        energy_adjusted_opex = opex_total
    else:
        non_energy = infer_non_energy_opex(opex_total, sec_kwh_m3, baseline_elec_price)
        energy_adjusted_opex = non_energy + (sec_kwh_m3 * elec_price)

    capex_component = 0.0
    if capex_per_m3_day is not None:
        capex_component = annualized_capex_per_m3(capex_per_m3_day, crf, utilization)

    return capex_component + energy_adjusted_opex

def compute_carbon(sec_kwh_m3: float | None, grid_kg_per_kwh: float, stated_carbon_cell: str) -> float:
    # If we have SEC, compute operational carbon from grid intensity.
    # If SEC is unknown (thermal), fall back to stated qualitative carbon.
    if sec_kwh_m3 is not None:
        return sec_kwh_m3 * grid_kg_per_kwh

    c = stated_carbon_cell.strip().lower()
    if "none" in c:
        return 0.0
    if "minimal" in c:
        return 0.2  # placeholder proxy for very low operational carbon
    # if numeric range exists, use midpoint-ish fallback
    n = parse_number(stated_carbon_cell)
    return n if n is not None else 0.5

def brine_ratio_value(cell: str) -> float:
    # Convert qualitative brine descriptions into a rough numeric proxy so
    # the model can consistently compare technologies on discharge burden.
    c = cell.strip().lower()
    if "no brine" in c:
        return 0.0
    if "minimal" in c:
        return 5.0  # interpret "minimal" as ~5%
    r = parse_range(cell.replace("%", ""))
    if r:
        return (r[0] + r[1]) / 2.0
    # fallback
    n = parse_number(cell)
    return n if n is not None else 25.0

# Future scenarios are external conditions that change the performance context
# around every technology. These do not change the technology definitions
# themselves; they change the world the technologies operate in.
FUTURES = {
    "Baseline": {
        # Baseline represents today's reference case.
        "elec_price": 0.10,          # $/kWh
        "grid_kg_per_kwh": 0.50,     # kg CO2e per kWh
        "capex_multiplier": 1.00,
        "opex_multiplier": 1.00,
        "brine_reg_threshold_pct": None,
        "brine_reg_penalty_pct": 0.0,
    },
    "EnergyPriceSpike": {
        # Grid electricity becomes more expensive and slightly dirtier.
        "elec_price": 0.25,
        "grid_kg_per_kwh": 0.55,
        "capex_multiplier": 1.00,
        "opex_multiplier": 1.00,
        "brine_reg_threshold_pct": None,
        "brine_reg_penalty_pct": 0.0,
    },
    "RenewablesCheaper": {
        # Clean electricity becomes cheaper, which helps electric processes.
        "elec_price": 0.05,
        "grid_kg_per_kwh": 0.20,
        "capex_multiplier": 1.05,  # slight capex premium for more renewables integration, optional
        "opex_multiplier": 1.00,
        "brine_reg_threshold_pct": None,
        "brine_reg_penalty_pct": 0.0,
    },
    "BrineRegTightens": {
        # Disposal requirements become stricter, penalizing high-brine options.
        "elec_price": 0.10,
        "grid_kg_per_kwh": 0.50,
        "capex_multiplier": 1.05,  # more outfall controls
        "opex_multiplier": 1.05,
        "brine_reg_threshold_pct": 20.0,  # >20% brine gets penalized
        "brine_reg_penalty_pct": 15.0,    # add +15% “effective brine burden”
    },
    "TechLearning": {
        # Manufacturing and deployment improve over time, reducing costs.
        "elec_price": 0.10,
        "grid_kg_per_kwh": 0.45,
        "capex_multiplier": 0.80,   # learning reduces capex
        "opex_multiplier": 0.95,    # learning reduces opex
        "brine_reg_threshold_pct": None,
        "brine_reg_penalty_pct": 0.0,
    },
}

# The next group of functions turns raw engineering/economic outputs into
# simple 0-5 MCDA scores. This makes very different metrics comparable.
def score_higher_better(x: float, bins: list[tuple[float, float, float]]) -> float:
    """
    bins: list of (low_inclusive, high_inclusive, score)
    """
    for lo, hi, sc in bins:
        if lo <= x <= hi:
            return sc
    # outside bins -> clamp
    if x < bins[0][0]:
        return bins[0][2]
    return bins[-1][2]

def score_lower_better(x: float, thresholds: list[tuple[float, float]]):
    """
    thresholds: list of (max_value, score), sorted ascending max_value
    """
    for maxv, sc in thresholds:
        if x <= maxv:
            return sc
    return thresholds[-1][1]

# Generic qualitative mapping. Some specific criteria use custom mappings
# below when directionality differs.
QUAL = {
    "very low": 5,
    "low": 4,
    "moderate": 3,
    "high": 2,
    "very high": 1,  # for complexity; we handle separately too
}

def score_recovery_from_pct(pct: float) -> float:
    # Higher recovery is better, so we invert the sign and reuse the
    # lower-is-better helper instead of creating a duplicate function.
    return score_lower_better(-pct, [(-80,5),(-60,4),(-45,3),(-30,2),(0,1)])

def score_complexity(cell: str) -> float:
    c = cell.strip().lower()
    mapping = {"very low":5,"low":4,"moderate":3,"high":2,"very high":1}
    return float(mapping.get(c, 3))

def score_reliability(cell: str) -> float:
    c = cell.strip().lower()
    mapping = {"very high":5,"high":4,"moderate":3,"low":2,"very low":1}
    return float(mapping.get(c, 3))

def score_startstop(cell: str) -> float:
    c = cell.strip().lower()
    mapping = {"very high":5,"high":4,"yes":3,"limited":2,"passive":3,"solar only":2}
    return float(mapping.get(c, 3))

def score_cleaning(cell: str) -> float:
    c = cell.strip().lower()
    if "minimal" in c:
        return 5
    if "6-12" in c:
        return 4
    if "6 months" in c:
        return 3
    if "1-3" in c:
        return 2
    return 3

def score_sec(sec: float | None) -> float:
    # Thermal technologies in this version do not have directly comparable
    # electric SEC values, so they get a neutral placeholder score until a
    # richer thermal accounting method is introduced.
    if sec is None:
        return 3.0
    return score_lower_better(sec, [(0.5,5),(1.0,4),(2.0,3),(999,2)])

def score_lcow(lcow: float) -> float:
    return score_lower_better(lcow, [(0.5,5),(1.0,4),(3.0,3),(999,2)])

def score_carbon(carbon: float) -> float:
    return score_lower_better(carbon, [(0.2,5),(0.5,4),(1.0,3),(999,2)])

def score_brine(brine_pct: float) -> float:
    return score_lower_better(brine_pct, [(0.0,5),(10.0,4),(20.0,3),(60.0,2),(999,1)])

def score_capex(capex_per_m3_day: float | None) -> float:
    if capex_per_m3_day is None:
        return 3.0
    return score_lower_better(capex_per_m3_day, [(500,5),(1500,4),(3000,3),(999999,2)])

def score_scalability(tech: str) -> float:
    # Scalability is currently a fixed expert-judgment score by technology.
    # If you later add better deployment data, this is a good place to plug
    # it in as a more evidence-based function.
    return {"RO":3.5,"ED":4.0,"HDH":4.0,"MSPD":4.0}.get(tech, 3.5)


# Each criterion belongs to one of four higher-level decision bins.
# Communities express preferences at the bin level; the model spreads those
# weights down to the underlying criteria automatically.
CRITERIA = ["Recovery","Reliability","Complexity","SEC","StartStop","Cleaning","Carbon","Brine","LCOW","CAPEX","Scalability"]
CRITERIA_TO_BIN = {
    "Recovery":0,"Reliability":0,"Complexity":0,
    "SEC":1,"StartStop":1,"Cleaning":1,
    "Carbon":2,"Brine":2,
    "LCOW":3,"CAPEX":3,"Scalability":3
}

def normalize(w: np.ndarray) -> np.ndarray:
    # Keep weight vectors well-behaved: no negative entries and total = 1.
    w = np.clip(w, 0, None)
    s = w.sum()
    return w / s if s > 0 else w

def rating_to_multiplier(rating: float) -> float:
    """Map a 1-5 community rating into a relative bin emphasis multiplier.

    3 is neutral, values below 3 reduce emphasis, and values above 3 increase
    emphasis. The interpolation keeps the change smooth rather than jumping
    abruptly between discrete categories.
    """
    return float(np.interp(rating, [1, 3, 5], [0.80, 1.00, 1.40]))

def derive_bin_priority_ratings(comm: CommunityProfile) -> Dict[str, float]:
    """Turn standardized community inputs into bin-level importance ratings.

    This keeps the transfer interface stable: users rate a community once on
    a shared template, and the model converts that into MCDA weights.
    """
    # Lower operator capacity means the community has less room to absorb
    # operational complexity, so we flip the scale here.
    operator_constraint = 6 - comm.operator_capacity
    return {
        "Technical": float(np.mean([comm.water_quality_risk, operator_constraint])),
        "Operations": float(np.mean([comm.energy_stress, operator_constraint])),
        "Environmental": float(comm.environmental_sensitivity),
        "Cost": float(np.mean([comm.cost_sensitivity, comm.growth_pressure])),
    }

def build_community_weight_model(comm: CommunityProfile) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Convert a high-level community profile into a weight model.

    The community only specifies a standard set of ratings.
    This helper turns that into:
    - a normalized base weight vector
    - a lower bound per bin
    - an upper bound per bin

    That means new communities can be added uniformly without hand-building
    custom weight vectors for each case.
    """
    base = DEFAULT_BIN_WEIGHTS.copy()
    for bin_name, rating in derive_bin_priority_ratings(comm).items():
        base[BIN_INDEX[bin_name]] *= rating_to_multiplier(rating)

    base = normalize(base)
    low = np.clip(base - comm.weight_flexibility, comm.minimum_bin_weight, comm.maximum_bin_weight)
    high = np.clip(base + comm.weight_flexibility, comm.minimum_bin_weight, comm.maximum_bin_weight)

    # Make sure the feasible band always contains the baseline weights.
    low = np.minimum(low, base)
    high = np.maximum(high, base)
    return base, low, high

def sample_bin_weights(base, low, high, n, rng):
    """Draw community preference weights for Monte Carlo ranking.

    We sample around the baseline mix using a Dirichlet draw, then clip the
    result to the allowed band so each community can explore uncertainty in
    priorities without drifting into unrealistic weight combinations.
    """
    base = normalize(base)
    # Larger alpha values keep draws closer to the baseline community view.
    alpha = np.maximum(base * 50, 1.0)
    draws = rng.dirichlet(alpha, size=n)
    out = []
    for d in draws:
        d = np.clip(d, low, high)
        out.append(normalize(d))
    return np.vstack(out)

def bin_to_criteria_weights(bin_w: np.ndarray) -> np.ndarray:
    """Spread each bin weight evenly across the criteria inside that bin.

    This is a simplifying assumption that keeps the model interpretable.
    If you later want finer control, this function is the place to introduce
    criterion-specific weights inside each bin.
    """
    bin_counts = {i: 0 for i in range(4)}
    for c in CRITERIA:
        bin_counts[CRITERIA_TO_BIN[c]] += 1
    w = np.zeros(len(CRITERIA))
    for i, c in enumerate(CRITERIA):
        b = CRITERIA_TO_BIN[c]
        w[i] = bin_w[b] / bin_counts[b]
    return normalize(w)

def passes_screening(comm_name: str, tech: str, comm: CommunityProfile) -> bool:
    # The first stage is a hard feasibility screen. We avoid scoring a
    # technology at all if it is incompatible with the community's source water.
    if comm.salinity_type not in TECH_COMPAT.get(tech, set()):
        return False
    # Add future hard screens here if you want to represent requirements such
    # as discharge limits, operator skill limits, or land constraints.
    return True

def simulate_one_tech_params(tech: str, rng: np.random.Generator):
    """Sample one uncertain realization for a technology.

    This is where literature ranges become a single draw for one Monte Carlo
    pass. The sampled parameters are still physical/economic values, not
    normalized MCDA scores.
    """
    # Pull the raw technology assumptions for the technology being simulated.
    d = TECH_DATA[tech]

    # SEC: treat "~0 (Thermal)" as None (unknown electric SEC)
    sec_cell = d["SEC (kWh/m³)"]
    sec = None if ("thermal" in sec_cell.lower() or "~0" in sec_cell) else sample_from_cell(sec_cell, rng)

    # CAPEX: "Variable" -> None (unknown)
    capex_cell = d["CAPEX ($/m³-d)"]
    capex = None if "variable" in capex_cell.lower() else sample_from_cell(capex_cell, rng)

    # OPEX: numeric even if "~$2.72"
    opex = sample_from_cell(d["OPEX ($/m³)"], rng)
    if opex is None:
        opex = 0.0

    # Recovery percent
    rec_rng = parse_range(d["Recovery Ratio"].replace("%",""))
    rec_pct = rng.uniform(rec_rng[0], rec_rng[1]) if rec_rng else 50.0

    # Brine ratio (%)
    brine_pct = brine_ratio_value(d["Brine Ratio"])

    return {
        "rec_pct": rec_pct,
        "sec": sec,
        "capex": capex,
        "opex": opex,
        "brine_pct": brine_pct,
        "reliability_cell": d["Reliability"],
        "complexity_cell": d["Complexity"],
        "startstop_cell": d["Start-Stop"],
        "cleaning_cell": d["Cleaning Freq."],
        "stated_carbon_cell": d["Carbon (kg/m³)"],
    }

def compute_scores_from_params(tech: str, params: dict, future: dict):
    """Apply a future scenario and translate raw parameters into 0-5 scores."""
    # Futures modify underlying parameters before scoring, which keeps the
    # ranking logic transparent and makes scenario assumptions easier to audit.
    # Start from the sampled raw parameters, then adjust them according to the
    # future scenario being evaluated.
    capex = params["capex"]
    if capex is not None:
        capex = capex * future["capex_multiplier"]

    opex = params["opex"] * future["opex_multiplier"]
    sec = params["sec"]

    # brine regulation: increase effective brine burden if above threshold
    brine = params["brine_pct"]
    thr = future["brine_reg_threshold_pct"]
    if thr is not None and brine > thr:
        brine = brine + future["brine_reg_penalty_pct"]

    # derive LCOW from capex + opex, with energy price affecting opex if SEC exists
    lcow = compute_lcow(
        capex_per_m3_day=capex,
        opex_total=opex,
        sec_kwh_m3=sec,
        elec_price=future["elec_price"],
        baseline_elec_price=FUTURES["Baseline"]["elec_price"],
        discount_rate=0.08,
        lifetime_years=20,
        utilization=0.90
    )

    carbon = compute_carbon(sec, future["grid_kg_per_kwh"], params["stated_carbon_cell"])

    # Convert physical/economic outcomes into normalized 0-5 MCDA scores.
    scores = {
        "Recovery": score_recovery_from_pct(params["rec_pct"]),
        "Reliability": score_reliability(params["reliability_cell"]),
        "Complexity": score_complexity(params["complexity_cell"]),
        "SEC": score_sec(sec),
        "StartStop": score_startstop(params["startstop_cell"]),
        "Cleaning": score_cleaning(params["cleaning_cell"]),
        "Carbon": score_carbon(carbon),
        "Brine": score_brine(brine),
        "LCOW": score_lcow(lcow),
        "CAPEX": score_capex(capex),
        "Scalability": score_scalability(tech),
    }
    # Return both the normalized MCDA scores and the underlying derived
    # quantities in case you want to audit or visualize them later.
    return scores, {"lcow": lcow, "carbon": carbon, "brine_eff": brine, "capex_eff": capex, "sec": sec}

def robust_run(communities: Dict[str, CommunityProfile] | None = None,
               n_param_samples=500,
               n_weight_samples=2000,
               seed=7):
    """Run the robust MCDA simulation across all communities and futures.

    For each community/future pair we:
    1. derive a bin-level weight model from the community profile,
    2. sample uncertain technology parameters,
    3. compute scores and rankings, and
    4. aggregate win rates and average ranks.
    """
    # A fixed seed makes runs reproducible, which is useful when comparing
    # model changes or communicating results.
    rng = np.random.default_rng(seed)
    communities = COMMUNITIES if communities is None else communities
    rows = []

    # Loop through communities one at a time so each one gets its own
    # feasibility screen and uncertainty-weight profile.
    for comm_name, comm in communities.items():
        # Build the community's weight model once, then reuse it across futures.
        base_bin, low, high = build_community_weight_model(comm)
        bin_draws = sample_bin_weights(base_bin, low, high, n_weight_samples, rng)
        feasible_techs = [tech for tech in TECH_DATA if passes_screening(comm_name, tech, comm)]

        if not feasible_techs:
            continue

        # Test each community under every future scenario.
        for future_name, future in FUTURES.items():
            win_counts = {t: 0 for t in feasible_techs}
            rank_sums = {t: 0.0 for t in feasible_techs}

            # sample parameters (deep uncertainty) and weights
            # First Monte Carlo loop: uncertain technology performance.
            for _ in range(n_param_samples):
                # build score table for this parameter sample under this future
                score_rows = []

                for tech in feasible_techs:
                    if not passes_screening(comm_name, tech, comm):
                        continue

                    p = simulate_one_tech_params(tech, rng)
                    score_dict, _derived = compute_scores_from_params(tech, p, future)
                    score_rows.append((tech, score_dict))

                # if nothing feasible, skip
                if not score_rows:
                    continue

                # Score matrix for this one simulated world state.
                S = pd.DataFrame({t: d for t, d in score_rows}).T[CRITERIA]

                # Each sampled weight vector represents one plausible stakeholder
                # preference mix for the same community.
                for bw in bin_draws:
                    cw = bin_to_criteria_weights(bw)
                    # Weighted-sum MCDA step.
                    total = S.dot(cw)
                    ranked = total.sort_values(ascending=False).index.tolist()
                    winner = ranked[0]
                    win_counts[winner] += 1
                    for r, t in enumerate(ranked, start=1):
                        rank_sums[t] += r

            runs = max(1, sum(win_counts.values()))
            for tech in feasible_techs:
                rows.append({
                    "community": comm_name,
                    "future": future_name,
                    "tech": tech,
                    "win_rate": win_counts[tech] / runs,
                    "avg_rank": (rank_sums[tech] / runs) if tech in rank_sums else None
                })

    return pd.DataFrame(rows)

def summarize_rankings(results: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return current (Baseline) winners and winners across all futures.

    This gives a concise decision summary while preserving the full scenario
    results table for deeper analysis.
    """
    winners = (
        results.sort_values(["community", "future", "win_rate"], ascending=[True, True, False])
               .groupby(["community", "future"])
               .head(1)
               [["community", "future", "tech", "win_rate", "avg_rank"]]
               .reset_index(drop=True)
    )
    current = winners[winners["future"] == "Baseline"].reset_index(drop=True)
    return current, winners

def analyze_community_dataset(source,
                              n_param_samples=400,
                              n_weight_samples=1500,
                              seed=7) -> dict:
    """Load a community CSV/DataFrame and run baseline plus future ranking."""
    # 1. Read and validate the incoming dataset.
    community_table = load_community_input_source(source)
    # 2. Convert rows into structured community objects.
    communities = load_communities_from_table(community_table)
    # 3. Run the robust ranking analysis for current and future conditions.
    results = robust_run(
        communities=communities,
        n_param_samples=n_param_samples,
        n_weight_samples=n_weight_samples,
        seed=seed,
    )
    # 4. Pull out compact reporting tables for decision-makers.
    current_winners, future_winners = summarize_rankings(results)
    return {
        "community_table": community_table,
        "communities": communities,
        "results": results,
        "current_winners": current_winners,
        "future_winners": future_winners,
    }
