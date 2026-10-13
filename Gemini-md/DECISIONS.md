# Technical Decisions Log

## Decision 1: Use SQLite for storage (2026-09-15)
We chose SQLite instead of a JSON file. It supports queries, handles concurrent access better, and requires no external server. A JSON file was rejected because it becomes slow and error-prone as the task list grows.

## Decision 2: Use argparse instead of Click (2026-09-17)
We chose the standard library argparse to avoid extra dependencies. Click was considered but rejected because the CLI is simple and does not justify a new package.

## Decision 3: Store timestamps in UTC (2026-09-22)
All task timestamps are stored in UTC using ISO 8601 format. Conversion to local time happens only when displaying to the user. This avoids bugs around daylight saving time.

## Decision 4: Adopt pytest as the testing framework (2026-10-02)
We chose pytest over unittest because of its simpler syntax and fixtures. All existing tests were migrated.

## Decision 5: Add a `priority` column to the tasks table (2026-10-07)
A new column `priority` (values: low, medium, high) was added to the tasks table. A migration script was created. The column `notes` was removed because it was unused.