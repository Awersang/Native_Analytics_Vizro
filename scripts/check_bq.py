"""
BigQuery connectivity & schema helper.

Run this after `gcloud auth application-default login` to confirm the app can
reach BigQuery and to inspect the table you want a dashboard to use.

Usage (PowerShell):

    # 1. Check that credentials work and list datasets in a project
    python scripts/check_bq.py --project YOUR_PROJECT

    # 2. List tables in a dataset
    python scripts/check_bq.py --project YOUR_PROJECT --dataset YOUR_DATASET

    # 3. Show a table's schema + a few sample rows (what I need to write a query)
    python scripts/check_bq.py --project YOUR_PROJECT --dataset YOUR_DATASET --table YOUR_TABLE

Once this prints a schema cleanly, paste the project/dataset/table here (or set
BQ_SAMPLE_PROJECT / BQ_SAMPLE_DATASET / BQ_SAMPLE_TABLE in your .env) and the
bq_sample dashboard will query live data.
"""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Check BigQuery access and inspect a table.")
    parser.add_argument("--project", required=True, help="GCP project ID that will run the query/billing.")
    parser.add_argument("--dataset", help="Dataset ID to inspect (may live in another project).")
    parser.add_argument("--table", help="Table or view ID to describe.")
    parser.add_argument(
        "--data-project",
        help="Project that owns the dataset, if different from --project (e.g. bigquery-public-data).",
    )
    parser.add_argument("--rows", type=int, default=5, help="Sample rows to preview (default 5).")
    args = parser.parse_args()

    try:
        from google.cloud import bigquery
    except ImportError:
        print(
            "google-cloud-bigquery is not installed.\n"
            "  pip install -r requirements.txt",
            file=sys.stderr,
        )
        return 2

    try:
        client = bigquery.Client(project=args.project)
    except Exception as exc:  # credentials / project errors
        print(
            "Could not create a BigQuery client. Most likely you need:\n"
            "  gcloud auth application-default login\n"
            f"Underlying error: {exc}",
            file=sys.stderr,
        )
        return 1

    data_project = args.data_project or args.project

    # ── No dataset → list datasets to confirm auth works ──────────────────────
    if not args.dataset:
        print(f"Credentials OK. Datasets visible in project '{data_project}':")
        for ds in client.list_datasets(project=data_project):
            print(f"  - {ds.dataset_id}")
        print("\nNext: re-run with --dataset <id> to list its tables.")
        return 0

    dataset_ref = f"{data_project}.{args.dataset}"

    # ── Dataset but no table → list tables ────────────────────────────────────
    if not args.table:
        print(f"Tables in {dataset_ref}:")
        for tbl in client.list_tables(dataset_ref):
            print(f"  - {tbl.table_id}")
        print("\nNext: re-run with --table <id> to see its schema.")
        return 0

    # ── Full ref → show schema + sample rows ──────────────────────────────────
    table_id = f"{dataset_ref}.{args.table}"
    table = client.get_table(table_id)
    print(f"Schema for {table_id}  ({table.num_rows:,} rows):")
    for field in table.schema:
        print(f"  {field.name:<32} {field.field_type:<12} {field.mode}")

    if args.rows > 0:
        print(f"\nSample ({args.rows} rows):")
        sql = f"SELECT * FROM `{table_id}` LIMIT {args.rows}"
        df = client.query(sql).to_dataframe()
        with_pd_options(df)
    return 0


def with_pd_options(df) -> None:
    import pandas as pd

    with pd.option_context("display.max_columns", None, "display.width", 200):
        print(df.to_string(index=False))


if __name__ == "__main__":
    raise SystemExit(main())
