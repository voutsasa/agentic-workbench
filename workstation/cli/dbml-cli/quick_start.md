---
tool: dbml-cli
updated: 2026-08-01
author: Achilleas Voutsas
version: 0.4.2
---

# dbml-cli — quick start

Converts between DBML — a plain-text database schema language — and SQL, in both directions, plus straight from a live database. The data-architecture counterpart to PlantUML and d2: schema as text, diffable in git.

## The three commands

| Command | Direction |
|---|---|
| `dbml2sql schema.dbml --postgres` | DBML → SQL DDL |
| `sql2dbml schema.sql --postgres` | SQL DDL → DBML |
| `db2dbml postgres '<connection-string>'` | live database → DBML |

All three write to stdout unless given `-o, --out-file <path>`.

## Dialects

`dbml2sql` targets `--mysql`, `--postgres`, `--mssql`, `--oracle`.

`sql2dbml` parses more, including legacy parsers for older dumps: `--mysql`, `--mysql-legacy`, `--postgres`, `--postgres-legacy`, `--mssql`, `--mssql-legacy`, `--snowflake`, `--oracle`.

`db2dbml` connects to `postgres`, `mysql`, `mssql`, `snowflake`, `bigquery`.

## db2dbml connection strings

```
db2dbml postgres 'postgresql://user:pass@localhost:5432/db?schemas=public'
db2dbml mysql    'mysql://user:pass@localhost:3306/db'
```

The `?schemas=` parameter restricts which schemas are read; without it you get everything, which on a real database is rarely what you want.

## Traps

- **Reach for the `-legacy` parser when `sql2dbml` chokes on a dump.** Older `mysqldump` and SQL Server output frequently needs it; the error otherwise looks like a syntax problem in your file.
- **Connection strings contain credentials.** `db2dbml` takes them as a shell argument, so they land in shell history. Prefer a variable read from `.env` over typing one inline.
- **DBML is the source of truth, not the SQL.** Round-tripping SQL → DBML → SQL does not preserve everything; treat `sql2dbml` as a way to *start* a DBML file, then maintain the DBML.

Docs: [CLI docs](https://dbml.dbdiagram.io/cli/) · full page ingest: [reference.md](reference.md)
