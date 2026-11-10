# Church_Scheduling_Problem
Modeling OR problem using Python Pulp

## Running

```
pip install -r requirements.txt
python run.py              # all scenarios; add --refresh to re-download the Google Sheets
```

Pipeline (`run.py`): download sheets -> feasible (person, task, block) triples
(`scheduling/triples.py`) -> fuzzy "Samen met" pairs (`scheduling/partners.py`) ->
PuLP model per scenario (`scheduling/model.py`) -> `outputs/<scenario>/` plus
`outputs/scenario_comparison.csv`. Settings, scenarios and weights live in
`scheduling/config.py`.

## Setup (private links)

Google Sheet IDs are kept out of git. Copy `scheduling/local_secrets.example.py` to
`scheduling/local_secrets.py` and fill in your sheet IDs (it is gitignored).
