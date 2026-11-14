---
tool: psql
updated: 2026-10-20
author: Achilleas Voutsas
version: 0.4.1
---

# psql — quick start

## Connect to Databricks Lakebase

`databricks psql` gets the OAuth token for you and starts `psql` with it. Arguments after `--` go to
`psql`:

```sh
databricks psql <instance> -- -d <database>                     # Lakebase Provisioned
databricks psql --project <project> -- -d <database>            # Lakebase Autoscaling
databricks psql <instance> -- -d <database> -c "SELECT 1"
```

With `psql` alone, keep the token in `PGPASSWORD`, not in the URL, so it stays out of your shell
history and the process list. A user that is an email is URL-escaped (`@` as `%40`):

```powershell
$env:PGPASSWORD = '<token>'
psql "postgresql://<user, @ as %40>@<host>/<database>?sslmode=require"
```

The Lakebase token used on 2026-10-19 was a JWT valid for one hour (`exp` − `iat` = 3600). When a
connection that worked starts failing with `password authentication failed`, get a new token.

## Run a script

```sh
psql "<url>" -v ON_ERROR_STOP=1 -f path/to/script.sql
```

Without `-v ON_ERROR_STOP=1`, `psql` reports an error and goes on to the next statement, and still
exits 0. In an interactive session, `\i 'C:/path/to/script.sql'` runs a file; use forward slashes,
even on Windows.

## Commands worth knowing

| Command | Effect |
|---|---|
| `\l` | List databases |
| `\dn` | List schemas |
| `\dt <schema>.*` | List the tables in a schema |
| `\c <database>` | Connect to another database on the same server |
| `\gexec` | Run each value the previous query returned as a statement |
| `\q` | Quit |

`\gexec` makes a script idempotent where SQL has no `IF NOT EXISTS`. `CREATE DATABASE` is one
such statement, and it also cannot run inside a transaction block:

```sql
SELECT 'CREATE DATABASE my_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'my_db')
\gexec
```

## Traps

- **Don't paste a connection string that has the token in it** into a chat, an issue or a tracked
  file. The token is the password.
- **`\gexec` and the other backslash commands are `psql`'s, not SQL.** A script that uses them
  runs only in `psql`, not in a web query editor or a Python driver.
