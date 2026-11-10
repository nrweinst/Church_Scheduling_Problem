"""Turn a solved Model into CSVs and a one-row metrics summary."""
import pandas as pd
import pulp

from . import config


def extract(model, people_names):
    t = model.triples
    chosen = t[[model.x[i].value() > 0.5 for i in t.index]]
    assignments = chosen[["person_id", "name", "task", "need_task", "block"]]\
        .sort_values(["block", "need_task", "name"]).reset_index(drop=True)

    assigned = assignments.groupby(["need_task", "block"]).size()
    coverage = pd.DataFrame(
        [(nt, b, need, int(assigned.get((nt, b), 0)))
         for (nt, b), need in sorted(model.needs.items(), key=lambda kv: (kv[0][1], kv[0][0]))],
        columns=["need_task", "block", "needed", "assigned"])
    coverage["shortfall"] = coverage.needed - coverage.assigned

    # per wanted pair: in how many shifts are they together, and why not otherwise
    together = {}
    for (a, b, nt, blk), v in model.y.items():
        together[(a, b)] = together.get((a, b), 0) + int(v.value() > 0.5)
    works = assignments.groupby("person_id").size()
    rows = []
    for a, b in sorted(model.pairs):
        shared = sum(1 for k in model.y if k[:2] == (a, b))
        n = together.get((a, b), 0)
        if n:
            why = "together"
        elif shared == 0:
            why = "no common feasible task/block"
        elif works.get(a, 0) == 0 or works.get(b, 0) == 0:
            why = "one or both not scheduled"
        else:
            why = "scheduled apart (task full / other rules)"
        rows.append((a, people_names[a], b, people_names[b], shared, n, why))
    pairs = pd.DataFrame(rows, columns=["person_a", "name_a", "person_b", "name_b",
                                        "common_options", "shifts_together", "status"])
    return assignments, coverage, pairs


def metrics(model, assignments, coverage, pairs):
    return {
        "sum_block_max_shortfall": int(round(sum(v.value() for v in model.block_max.values()))),
        "total_shortfall": int(coverage.shortfall.sum()),
        "slots_filled": int(coverage.assigned.sum()),
        "slots_needed": int(coverage.needed.sum()),
        "people_scheduled": int(assignments.person_id.nunique()),
        "paired_shifts": int(round(sum(v.value() for v in model.y.values()))),
        "pairs_together_at_least_once": int((pairs.shifts_together > 0).sum()),
        "pairs_total": len(pairs),
        "pairs_with_no_common_option": int((pairs.common_options == 0).sum()),
        "people_with_2plus_disciplines": int(round(sum(v.value() for v in model.variety.values()))),
    }


def save(name, assignments, coverage, pairs):
    out = config.OUTPUT_DIR / name
    out.mkdir(parents=True, exist_ok=True)
    assignments.to_csv(out / "assignments.csv", index=False)
    coverage.to_csv(out / "coverage.csv", index=False)
    pairs.to_csv(out / "pairs.csv", index=False)
