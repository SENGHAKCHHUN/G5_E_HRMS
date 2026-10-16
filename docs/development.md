# Development

[← Back to README](../README.md)

## Tests and Linting

```bash
pytest          # uses a temporary database; hr_system.db is not touched
ruff check .    # configuration in pyproject.toml
```

The tests cover the API, business rules, the layer structure, database migration, translations,
the frontend logic, and a smoke test that opens every screen for each role (needs a display).

## Database Migrations (Alembic)

The server applies migrations automatically at start-up, and older databases are upgraded with their
data kept. After changing `backend/models.py`, create a migration and commit it:

```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head        # apply now (the server also does this at start-up)
alembic current             # show the database's current migration
```

## Translations (English / Khmer)

Texts are written in English in the code and translated with gettext catalogs:

| Part | Marked in code with | Catalog |
|---|---|---|
| Desktop screens | `_("...")`, `N_("...")` | `frontend/locales/km/LC_MESSAGES/hrms.po` |
| Server messages | `t("...")`, `gettext_("...")`, `N_("...")`, and the message of `NotFound`, `Conflict`, ... | `backend/locales/km/LC_MESSAGES/api.po` |

Use `{name}` placeholders instead of joining strings, so translators can reorder words:
`_("Showing {start}-{end} of {total}").format(...)`.

After adding or changing texts, run from the project root:

```bash
# 1. collect the texts into the templates
pybabel extract -k _ -k N_ --no-location --sort-output --project=HRMS -o frontend/locales/hrms.pot frontend
pybabel extract -k t -k gettext_ -k N_ -k DomainError -k BadRequest -k Unauthorized -k Forbidden -k NotFound \
    -k Conflict -k TooManyRequests -k ExternalServiceError --no-location --sort-output --project=HRMS \
    -o backend/locales/api.pot backend

# 2. add new texts to the Khmer catalogs, then translate them (e.g. with Poedit)
pybabel update -i frontend/locales/hrms.pot -d frontend/locales -D hrms
pybabel update -i backend/locales/api.pot -d backend/locales -D api

# 3. compile the .mo files the apps read
pybabel compile -d frontend/locales -D hrms
pybabel compile -d backend/locales -D api
```

`scripts/fill_translations.py` merges a dict of translations into a catalog for bulk updates.
`tests/frontend/test_translations.py` fails if a text is untranslated, placeholders differ, or a `.mo` file is stale.
