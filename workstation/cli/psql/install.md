---
tool: psql
command: psql
product: PostgreSQL client (psql)
verified: 2026-10-20
author: Achilleas Voutsas
version: 0.4.1
---

# psql — install

Binary: `psql`, PostgreSQL's interactive terminal. In this workbench it runs SQL scripts against
PostgreSQL databases, Databricks Lakebase included. `databricks psql` is a wrapper around it, and
needs it on `PATH`: its help says "Requires psql to be installed."

| Platform | Command |
|---|---|
| Windows | `scoop install postgresql` |
| macOS | `brew install libpq` |

**The user runs it, never the agent.** Which route a given machine actually used, and which version
it fetched, is install status. That goes in the machine's file under
[`../../machines/`](../../machines/), not here.

Verify with `psql --version`. It prints `psql (PostgreSQL) <x.y>`, e.g. `psql (PostgreSQL) 18.6`.

## Traps

- **On Windows, Scoop's `postgresql` is the whole server, not just the client.** It installs
  EnterpriseDB's binaries zip, and its `post_install` runs `initdb` with superuser `postgres` and a
  blank password into `scoop\persist\postgresql\data`. It also sets `PGDATA`, `PG_LIB_DIR` and
  `PG_INCLUDE_DIR`, and adds a pgAdmin 4 shortcut (`scoop cat postgresql`). Nothing listens until
  someone runs `pg_ctl start`. Don't start that server unless you want a local database: its
  superuser has no password.
- **No shim: Scoop puts `scoop\apps\postgresql\current\bin` on the user `PATH`** (`env_add_path`).
  A terminal, or an agent session, started before the install doesn't see `psql`. Open a new one.
- **On macOS, `libpq` is keg-only** ("it conflicts with PostgreSQL"), so Homebrew does not put
  `psql` on `PATH`. Add `$(brew --prefix libpq)/bin` to `PATH` in your shell profile.
- **Windows warns `Console code page (437) differs from Windows code page (1252)`** at every start.
  The warning is harmless for ASCII scripts. To silence it, run `chcp 1252` before `psql` (psql
  reference, *Notes for Windows Users*).

Docs: [psql](https://www.postgresql.org/docs/current/app-psql.html)
