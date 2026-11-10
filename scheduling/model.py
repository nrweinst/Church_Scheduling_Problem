"""PuLP model: assign people to (task, block) shifts from the feasible triples."""
from collections import defaultdict

import pulp

from . import config


class Model:
    """Variables and hard constraints shared by every scenario.

    x[i]            1 if feasible triple i is worked (one binary per triple)
    short[nt,b]     unfilled slots for need row nt in block b
    block_max[b]    worst shortfall over all tasks in block b
    y[a,b,nt,k]     1 if paired people a and b both work need row nt in block k
    variety[p]      1 if person p works 2+ different disciplines
    """

    def __init__(self, triples, needs, pairs):
        self.triples, self.needs, self.pairs = triples, needs, pairs
        self.prob = pulp.LpProblem("church_scheduling", pulp.LpMinimize)
        self.x = {i: pulp.LpVariable(f"x_{i}", cat="Binary") for i in triples.index}

        by_person_block = defaultdict(list)
        by_need = defaultdict(list)
        by_person_need = defaultdict(list)      # (person, need_task, block) -> triples
        by_person_task = defaultdict(list)
        for i, r in triples.iterrows():
            by_person_block[(r.person_id, r.block)].append(i)
            by_need[(r.need_task, r.block)].append(i)
            by_person_need[(r.person_id, r.need_task, r.block)].append(i)
            by_person_task[(r.person_id, r.task)].append(i)

        # one task per person per block
        for key, idx in by_person_block.items():
            self.prob += pulp.lpSum(self.x[i] for i in idx) <= 1, f"one_task_{key}"

        # at most MAX_SHIFTS_IN_ROW consecutive blocks worked
        n, last = config.MAX_SHIFTS_IN_ROW, max(b for _, b in needs)
        for p in triples.person_id.unique():
            for start in range(1, last - n + 1):
                window = [i for b in range(start, start + n + 1)
                          for i in by_person_block.get((p, b), [])]
                if window:
                    self.prob += (pulp.lpSum(self.x[i] for i in window) <= n,
                                  f"in_a_row_{p}_{start}")

        # coverage: never over-fill a need row; shortfall measured against it
        self.short = {}
        for k, need in needs.items():
            assigned = pulp.lpSum(self.x[i] for i in by_need.get(k, []))
            self.short[k] = pulp.LpVariable(f"short_{len(self.short)}", 0, need)
            self.prob += assigned <= need, f"cap_{k}"
            self.prob += self.short[k] >= need - assigned, f"short_def_{k}"
        self.block_max = {}
        for b in sorted({b for _, b in needs}):
            self.block_max[b] = pulp.LpVariable(f"block_max_{b}", 0)
            for k in needs:
                if k[1] == b:
                    self.prob += self.block_max[b] >= self.short[k], f"bm_{b}_{k[0]}"

        # pairing: y <= worked(a, nt, k) and y <= worked(b, nt, k).
        # Continuous is enough: the objective pushes y up to min(.,.), which is 0 or 1.
        self.y = {}
        for a, b in sorted(pairs):
            keys = ({(nt, blk) for (p, nt, blk) in by_person_need if p == a}
                    & {(nt, blk) for (p, nt, blk) in by_person_need if p == b})
            for nt, blk in sorted(keys):
                v = pulp.LpVariable(f"y_{a}_{b}_{len(self.y)}", 0, 1)
                self.y[(a, b, nt, blk)] = v
                for person in (a, b):
                    idx = by_person_need[(person, nt, blk)]
                    self.prob += v <= pulp.lpSum(self.x[i] for i in idx)

        # variety (soft): reward people who work 2+ different disciplines.
        # z[p,t] <= shifts worked at t; variety[p] <= (#disciplines worked) - 1
        self.variety = {}
        tasks_of = defaultdict(list)
        for (p, t) in by_person_task:
            tasks_of[p].append(t)
        for p, ts in tasks_of.items():
            if len(ts) < 2:
                continue
            z = {t: pulp.LpVariable(f"z_{p}_{j}", cat="Binary") for j, t in enumerate(ts)}
            for t in ts:
                self.prob += z[t] <= pulp.lpSum(self.x[i] for i in by_person_task[(p, t)])
            self.variety[p] = pulp.LpVariable(f"variety_{p}", 0, 1)
            self.prob += self.variety[p] <= pulp.lpSum(z.values()) - 1

    # objective pieces
    def sum_block_max(self):
        return pulp.lpSum(self.block_max.values())

    def total_short(self):
        return pulp.lpSum(self.short.values())

    def paired_shifts(self):
        return pulp.lpSum(self.y.values())

    def variety_people(self):
        return pulp.lpSum(self.variety.values())

    def solve(self, objective):
        self.prob.setObjective(objective)
        status = self.prob.solve(pulp.PULP_CBC_CMD(
            msg=False, timeLimit=config.SOLVER_TIME_LIMIT, gapRel=0))
        if pulp.LpStatus[status] != "Optimal":
            raise RuntimeError(f"solver status: {pulp.LpStatus[status]}")
        return pulp.value(objective)


def solve_scenario(triples, needs, pairs, spec):
    """Solve one scenario and return the Model with its variables set."""
    m = Model(triples, needs, pairs)
    if spec["type"] == "lexicographic":
        # each stage is fixed (with a tiny tolerance) before the next is optimised
        stages = [(m.sum_block_max(), "min"), (m.total_short(), "min"),
                  (m.paired_shifts(), "max"), (m.variety_people(), "max")]
        for expr, sense in stages:
            best = m.solve(expr if sense == "min" else -expr)
            best = best if sense == "min" else -best
            m.prob += (expr <= best + 1e-6) if sense == "min" else (expr >= best - 1e-6)
    else:
        m.solve(spec["w_max"] * m.sum_block_max() + spec["w_total"] * m.total_short()
                - spec["w_pair"] * m.paired_shifts()
                - spec["w_variety"] * m.variety_people())
    return m
