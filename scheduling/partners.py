"""Fuzzy-match the free-text "Samen met" field to other volunteers' full names.

Only high-confidence, non-alternative matches are marked `use` and treated as
"want to work together" pairs by the model.
"""
import re
import unicodedata

import pandas as pd
from rapidfuzz import fuzz

from . import config

# "A of B" / "A or B" / "A/B": the person gave alternatives, not a firm group.
ALTERNATIVE = re.compile(r"\bof\b|/|\bor\b", re.IGNORECASE)


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s.lower())).strip()


def match_partners(people):
    people = people.assign(full=people["name"].map(norm))
    # duplicate submissions: link to the most recent row for each name
    latest = people.sort_values("submitted").drop_duplicates("full", keep="last")
    candidates = latest[latest.full.str.count(" ") >= 1]  # need first + last name

    rows = []
    for p in people[people.together_with.str.strip() != ""].itertuples():
        text = norm(p.together_with)
        for c in candidates.itertuples():
            if c.person_id == p.person_id or c.full == p.full:
                continue
            score = fuzz.partial_ratio(c.full, text)
            if score >= config.MATCH_THRESHOLD:
                rows.append((p.person_id, p.name, c.person_id, c.name, round(score, 1),
                             bool(ALTERNATIVE.search(p.together_with)), p.together_with))
    m = pd.DataFrame(rows, columns=["person_id", "name", "partner_id", "partner_name",
                                    "score", "is_alternative", "raw_text"])
    m["use"] = ~m.is_alternative
    m["needs_review"] = m.score < config.REVIEW_BELOW
    unmatched = people[(people.together_with.str.strip() != "")
                       & ~people.person_id.isin(m.person_id)]
    return m, unmatched[["person_id", "name", "together_with"]]


def partner_pairs(matches):
    """Undirected {(a, b)} pairs (a < b) that want to work together."""
    used = matches[matches.use]
    return {tuple(sorted(x)) for x in zip(used.person_id, used.partner_id)}
