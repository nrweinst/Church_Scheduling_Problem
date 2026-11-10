"""Build the set of feasible (person, task, block) triples for the model.

A triple is feasible when the person is available in the block, chose the task,
the task runs in that block, and the person's age fits the task's age range.
"""
import re

import pandas as pd

from . import config


def load_needs():
    """Return {(need_task, plan_block): volunteers needed}."""
    raw = pd.read_csv(config.NEEDS, header=None, skiprows=1)
    blocks = [int(re.search(r"BLOK (\d+)", c).group(1)) for c in raw.iloc[0, 1:]]
    needs = {}
    for _, row in raw.iloc[1:].iterrows():
        for b, n in zip(blocks, row.iloc[1:]):
            if pd.notna(n):
                needs[(row.iloc[0], b)] = int(n)
    return needs


def load_people():
    f = pd.read_csv(config.FORM)
    return pd.DataFrame({
        "person_id": f.index,
        "name": f["Voornaam"].str.strip() + " " + f["Achternaam"].str.strip(),
        "age": f["Leeftijd"],
        "form_blocks": f.iloc[:, 10].fillna("").map(
            lambda s: {int(n) for n in re.findall(r"BLOK (\d+)", s)}),
        "tasks": f.iloc[:, 11].fillna("").map(
            lambda s: {t.strip() for t in s.split(",") if t.strip()}),
        "together_with": f["Samen met"].fillna("").astype(str),
        "submitted": pd.to_datetime(f["Tijdstempel"]),
    })


def build_triples(people, needs):
    ages = pd.read_csv(config.AGES).set_index("Discpline")

    # task offered in block -> the need row that slot counts towards
    slots = {}
    for (need_task, block) in needs:
        for task in config.COMBINED_TASKS.get(need_task, [need_task]):
            slots.setdefault(task, {})[block] = need_task

    rows = []
    for p in people.itertuples():
        for task in p.tasks:
            if task not in ages.index or task not in slots:
                continue
            lo, hi = ages.loc[task, ["min age", "max age"]]
            if not lo <= p.age <= hi:
                continue
            for block, need_task in slots[task].items():
                if set(config.PLAN_BLOCK_REQUIRES[block]) <= p.form_blocks:
                    rows.append((p.person_id, p.name, task, block, need_task))
    return pd.DataFrame(
        rows, columns=["person_id", "name", "task", "block", "need_task"])


def report(people, needs, triples):
    print(f"  {len(triples)} feasible triples for {triples.person_id.nunique()} of "
          f"{len(people)} people")
    supply = triples.groupby(["need_task", "block"]).person_id.nunique()
    short = [(t, b, supply.get((t, b), 0), n) for (t, b), n in needs.items()
             if supply.get((t, b), 0) < n]
    print(f"  {len(short)} of {len(needs)} (task, block) cells have fewer eligible "
          "people than needed")
