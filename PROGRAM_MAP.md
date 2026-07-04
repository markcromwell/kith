# Program Map: Kith

<!--GENERATED:BEGIN hash=c352189051711bae25f99ae23c92aa315073b3401ed322f510a3d601d68df667 sig= job=0 commit=c85e6acee210e05e522b2c7378afbb68de3477fb-->
<!--Generated 2026-07-04T08:55:58.197278+00:00. Do not edit — will be overwritten.-->

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
app/overdue.py
app/routers/__init__.py
app/routers/home.py
app/routers/people.py
app/templates/home.html
app/templates/people_form.html
app/templates/people_list.html
app/templates/person_detail.html
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
scripts/test_interactions.py
scripts/test_migration.py
scripts/test_people.py
scripts/test_unit.py
```

## IV. API Surface [GENERATED — do not edit]

| Method | Path | Status Code |
|--------|------|-------------|
| GET | `/` | 200 |
| GET | `/health` | 200 |
| GET | `/people` | 200 |
| POST | `/people` | 200 |
| GET | `/people/new` | 200 |
| GET | `/people/{person_id}` | 200 |
| POST | `/people/{person_id}` | 200 |
| POST | `/people/{person_id}/delete` | 200 |
| GET | `/people/{person_id}/edit` | 200 |
| POST | `/people/{person_id}/interactions` | 200 |
| POST | `/people/{person_id}/reached-out` | 200 |

<!--GENERATED:END-->

---

## V. Architectural Decisions [CURATED]
_No decisions recorded yet._

---

## VI. Planned Work [CURATED]
_To be populated by the spec planner._
