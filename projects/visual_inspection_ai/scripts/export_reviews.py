import argparse

import _bootstrap
from inspection_ai.config import AppConfig
from inspection_ai.db import Database
from inspection_ai.reporting.export import export_inspection_summary, export_reviews_csv


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=["csv", "json"], default="csv")
    parser.add_argument("--status")
    args = parser.parse_args()
    config = AppConfig()
    db = Database(config.paths.database)
    path = export_reviews_csv(db, config.paths.reports, args.status) if args.format == "csv" else export_inspection_summary(db, config.paths.reports)
    print(path)


if __name__ == "__main__":
    main()
