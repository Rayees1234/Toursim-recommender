"""
ETL Module: Extract
Extracts raw data from data/raw/india_tourism_dataset.json and validates initial schema.
"""

import json
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def extract_raw_data(file_path=None):
    if file_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(base_dir, "data", "raw", "india_tourism_dataset.json")
        if not os.path.exists(file_path):
            file_path = os.path.join(base_dir, "india_tourism_dataset.json")

    logger.info(f"Extracting raw tourism data from: {file_path}")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Source raw data file not found at {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array of records, but received {type(data)}")

    record_count = len(data)
    logger.info(f"Extracted {record_count} raw destination records successfully.")
    return data


if __name__ == "__main__":
    records = extract_raw_data()
    print(f"Extraction test successful: {len(records)} records extracted.")
