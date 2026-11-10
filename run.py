"""Single entry point: data -> feasible triples -> partner pairs -> solve -> outputs.

    python run.py                      # use downloaded data if present, run all scenarios
    python run.py --refresh            # re-download the Google Sheets first
    python run.py --scenario pairing_first
"""
import argparse
import time

import pandas as pd

from scheduling import config, partners, reporting, sheets, triples
from scheduling.model import solve_scenario


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--refresh", action="store_true", help="re-download the Google Sheets")
    ap.add_argument("--scenario", choices=["all", *config.SCENARIOS], default="all")
    args = ap.parse_args()

    print("1. Data")
    if args.refresh or not sheets.raw_data_present():
        sheets.download_sheets()
    else:
        print("  using existing CSVs in data/ (pass --refresh to re-download)")

    print("2. Feasible (person, task, block) triples")
    people, needs = triples.load_people(), triples.load_needs()
    feasible = triples.build_triples(people, needs)
    triples.report(people, needs, feasible)

    print("3. Partner pairs from 'Samen met'")
    matches, unmatched = partners.match_partners(people)
    pairs = partners.partner_pairs(matches)
    print(f"  {len(pairs)} firm pairs; {matches.needs_review.sum()} matches to review; "
          f"{len(unmatched)} entries unmatched")

    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    feasible.to_csv(config.PROCESSED_DIR / "feasible_triples.csv", index=False)
    matches.to_csv(config.PROCESSED_DIR / "partner_matches.csv", index=False)
    unmatched.to_csv(config.PROCESSED_DIR / "partner_unmatched.csv", index=False)

    print("4. Solve")
    names = dict(zip(people.person_id, people.name))
    summary = {}
    for name, spec in config.SCENARIOS.items():
        if args.scenario not in ("all", name):
            continue
        t0 = time.time()
        model = solve_scenario(feasible, needs, pairs, spec)
        a, c, p = reporting.extract(model, names)
        reporting.save(name, a, c, p)
        summary[name] = reporting.metrics(model, a, c, p)
        print(f"  {name}: solved in {time.time() - t0:.1f}s")

    table = pd.DataFrame(summary)
    config.OUTPUT_DIR.mkdir(exist_ok=True)
    table.to_csv(config.OUTPUT_DIR / "scenario_comparison.csv")
    print("\n5. Scenario comparison (details in outputs/)\n")
    print(table.to_string())


if __name__ == "__main__":
    main()
