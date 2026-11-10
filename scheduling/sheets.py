"""Download every tab of each Google Sheet and save each as a CSV in data/<label>/."""
import re

import pandas as pd

from . import config


def download_sheets():
    for label, sheet_id in config.SHEETS.items():
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
        out_dir = config.RAW_DIR / label
        out_dir.mkdir(parents=True, exist_ok=True)
        for name, df in pd.read_excel(url, sheet_name=None).items():
            path = out_dir / f"{re.sub(r'[^\w\- ]', '_', name).strip()}.csv"
            df.to_csv(path, index=False)
            print(f"  {label}/{name}: {df.shape[0]} rows x {df.shape[1]} cols")


def raw_data_present():
    return all(p.exists() for p in (config.FORM, config.NEEDS, config.AGES))
