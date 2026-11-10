"""Template for local_secrets.py (which is gitignored). Copy it and fill in real IDs."""

# label -> Google Sheet ID (the long string in the sheet's URL between /d/ and /edit).
# Sheets must be shared as "anyone with the link can view".
# The labels must stay "planning_inputs" and "form_responses" - config.py uses them
# to find the downloaded CSV folders.
SHEETS = {
    "planning_inputs": "<sheet id of the planning inputs workbook>",
    "form_responses": "<sheet id of the form responses workbook>",
}
