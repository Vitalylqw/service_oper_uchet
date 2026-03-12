> Historical migrations archive. Do not use as the active Alembic history.

# Archived Alembic History

These files preserve the pre-baseline migration chain exactly as it existed before the repository
was switched to a single baseline migration on 2026-03-08.

Why archived:
- the active history contained a duplicate `revision = "0003"` conflict;
- standard Alembic commands (`history`, `branches`, `upgrade head --sql`) were broken;
- the project moved to one canonical baseline for clean databases.

How to use:
- `migrations/versions/` is the only active Alembic history;
- files in this directory are for project memory, audit, and manual investigation only;
- do not move these archived files back into the active `versions/` directory.
