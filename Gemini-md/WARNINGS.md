# Sensitive Areas - Do Not Change Without Testing

## Warning 1: Database migration script (severity: high)
The file `todo/migrations.py` modifies the live database schema. Do not edit it without running the full test suite and backing up `tasks.db`. A mistake here can cause permanent data loss.
Last reviewed: 2026-10-07

## Warning 2: Timestamp handling in `models.py` (severity: medium)
All timestamps must remain in UTC. Changing the timezone logic can silently break sorting and the overdue-task calculation. Do not touch this code without testing.
Last reviewed: 2026-10-05

## Warning 3: Command-line argument parsing (severity: medium)
Changing flag names in `cli.py` breaks existing user scripts. Any change to flags must be backward compatible, or documented as a breaking change.
Last reviewed: 2026-10-09

## Known Technical Limitation
SQLite allows only one writer at a time. This limitation is mentioned in several decisions. Do not run multiple instances of the app writing to the same database file in parallel.