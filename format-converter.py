"""
Convert the CSV files in data/ to Parquet.

The current data files are always re-converted; dated snapshot files
("YYYY-MM-DD *.csv") are only converted once.
"""

import os
import re

import polars as pl

DATA_FOLDER = "data"
DATED = re.compile(r"^\d{4}-\d{2}-\d{2} ")

for file_name in sorted(os.listdir(DATA_FOLDER)):
    if not file_name.endswith(".csv"):
        continue
    csv_path = os.path.join(DATA_FOLDER, file_name)
    parquet_path = csv_path[:-4] + ".parquet"
    if DATED.match(file_name) and os.path.exists(parquet_path):
        continue
    try:
        df = pl.read_csv(csv_path, infer_schema_length=None)
        df.write_parquet(parquet_path)
        print("Exported %s -> %s" % (csv_path, parquet_path))
    except Exception as e:
        print("Could not convert %s: %s" % (csv_path, e))
