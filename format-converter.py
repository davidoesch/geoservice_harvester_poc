import os
import polars as pl

data_folder = "data"

for file_name in os.listdir(data_folder):
    if file_name.endswith('.csv'):
        csv_file_path = os.path.join(data_folder, file_name)
        parquet_file_path = os.path.join(data_folder, file_name.replace('.csv', '.parquet'))
        if not os.path.exists(parquet_file_path):
            df = pl.read_csv(csv_file_path)
            df.write_parquet(parquet_file_path)
            print("Exported CSV file to Parquet: %s" % parquet_file_path)
