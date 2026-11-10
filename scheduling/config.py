"""All paths, source sheets and tunable settings in one place."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data"                # CSVs downloaded from Google Sheets
PROCESSED_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = ROOT / "outputs"

# Private sheet IDs live in scheduling/local_secrets.py (gitignored).
try:
    from .local_secrets import SHEETS
except ImportError as e:
    raise SystemExit(
        "Missing scheduling/local_secrets.py - copy scheduling/local_secrets.example.py "
        "to scheduling/local_secrets.py and fill in your Google Sheet IDs.") from e
FORM = RAW_DIR / "form_responses" / "Formulierreacties 1.csv"
NEEDS = RAW_DIR / "planning_inputs" / "number of volunteers needed.csv"
AGES = RAW_DIR / "planning_inputs" / "ages per discipline.csv"

# The form has 4 availability blocks (10-13, 13-16, 16-20, 20-23) but the planning
# sheet has 7 two-hour blocks. A planning block is allowed only if the person ticked
# ALL the form blocks listed here (e.g. 12-14 straddles 13:00, so needs form 1 and 2).
# Edit this mapping once the blocks get aligned.
PLAN_BLOCK_REQUIRES = {1: [1], 2: [1, 2], 3: [2], 4: [3], 5: [3], 6: [4], 7: [4]}

# The needs sheet combines these into one row; the age sheet lists them separately.
COMBINED_TASKS = {"garderobe-koffiehoek-toiletten": ["garderobe-koffiehoek", "toiletten"]}

# --- partner ("Samen met") matching ---
MATCH_THRESHOLD = 88   # 0-100 fuzzy score below which a name is not considered mentioned
REVIEW_BELOW = 95      # matches under this score are flagged for manual review

# --- model rules ---
MAX_SHIFTS_IN_ROW = 2

# Scenarios, solved independently and compared.
#   coverage_first: strict priority order (each stage is fixed before the next):
#       1) minimise sum over blocks of the worst per-task shortfall in that block
#       2) minimise total shortfall   3) maximise paired shifts   4) maximise variety
#   pairing_first: one weighted objective where a paired shift is worth more than
#       a covered slot:  minimise  w_max*sum(block max shortfall) + w_total*total
#       shortfall - w_pair*paired shifts - w_variety*people with 2+ disciplines
SCENARIOS = {
    "coverage_first": {"type": "lexicographic"},
    "pairing_first": {"type": "weighted", "w_max": 1.0, "w_total": 1.0,
                      "w_pair": 2.0, "w_variety": 0.01},
}
SOLVER_TIME_LIMIT = 300  # seconds per solve
