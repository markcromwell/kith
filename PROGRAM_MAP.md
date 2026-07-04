# Program Map: Kith

<!--GENERATED:BEGIN hash=11c4b5fd161944b695b65e330ca4442042bb920c98fbea7324260d1a312e90c1 sig= job=0 commit=20ad19f9b06d6c510623986ac8563b58ffacf17a-->
<!--Generated 2026-07-04T06:15:37.519364+00:00. Do not edit — will be overwritten.-->

## II. Canonical Data Schema [GENERATED — do not edit]

### `interaction`

| Column | Type | Nullable | Default |
|--------|------|----------|---------|

### `person`

| Column | Type | Nullable | Default |
|--------|------|----------|---------|

## III. File and Module Map [GENERATED — do not edit]

```
.dockerignore
.env.example
.github/workflows/ci.yml
.gitignore
Dockerfile
PROGRAM_MAP.md
README.md
alembic.ini
alembic/env.py
alembic/script.py.mako
alembic/versions/0001_baseline.py
app/__init__.py
app/config.py
app/db.py
app/health.py
app/models.py
app/routers/__init__.py
app/routers/home.py
app/templates/home.html
docker-compose.yml
main.py
pyproject.toml
requirements.in
requirements.lock
scripts/__init__.py
scripts/setup.py
scripts/smoke_boot.py
scripts/test_db.py
scripts/test_home.py
scripts/test_migration.py
scripts/test_unit.py
```

## IV. API Surface [GENERATED — do not edit]

| Method | Path | Status Code |
|--------|------|-------------|
| GET | `/` | 200 |
| GET | `/health` | 200 |

<!--GENERATED:END-->

---

## V. Architectural Decisions [CURATED]
_No decisions recorded yet._

---

## VI. Planned Work [CURATED]
_To be populated by the spec planner._
