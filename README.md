# CSCI 341 Assignment 3 – Research Conference and Paper Review Management System

PostgreSQL database, Python/SQLAlchemy query program (Part 2) and Flask web application
(Part 3) implementing the Assignment 1 model.

## Contents

| Path | Purpose |
|---|---|
| `sql/schema.sql` | `CREATE TABLE` statements with all keys and constraints (re-runnable) |
| `sql/view.sql` | `accepted_paper_schedule` view |
| `sql/seed.sql` | Sample data |
| `sql/conference_db_dump.sql` | Plain `pg_dump` export of schema, seed data and view |
| `db.py` | SQLAlchemy engine and helpers that execute the SQL scripts |
| `setup_db.py` | Recreates the schema and restores the initial dataset |
| `part2_queries.py` | Part 2 tasks 1–8 (prints SQL, parameters and results) |
| `part2_output.txt` | Output of `part2_queries.py` against the seed data |
| `app.py`, `templates/` | Part 3 Flask web application |
| `requirements.txt`, `Procfile`, `render.yaml` | Dependencies and deployment configuration |
| `EXECUTIVE_SUMMARY.md`, `links.txt` | Executive summary and links |

## Software versions

- PostgreSQL 16.15
- Python 3.12.3
- SQLAlchemy 2.1.9, psycopg2-binary 2.9.13
- Flask 3.1.3, gunicorn 27.0.1

## Setup and database restoration

```bash
pip install -r requirements.txt

# Create a database and user (once)
sudo -u postgres psql -c "CREATE ROLE conf LOGIN PASSWORD 'conf';"
sudo -u postgres psql -c "CREATE DATABASE conference_db OWNER conf;"

# Optional: point to another database (default shown)
export DATABASE_URL=postgresql+psycopg2://conf:conf@localhost:5432/conference_db
```

Restore the initial dataset with **either** of:

```bash
python setup_db.py                                   # drops, recreates and reseeds via SQLAlchemy
psql -h localhost -U conf -d conference_db -f sql/conference_db_dump.sql   # into an empty database
```

`python part2_queries.py` also recreates and reseeds the database (tasks 1–2) before running the
other tasks.

## Running Part 2

```bash
python part2_queries.py > part2_output.txt
```

Every statement is executed with SQLAlchemy `text()` and bound parameters. Output is labelled
with task numbers and shows each SQL statement, its parameters and its result. Updates and
deletions show before/after results inside a transaction that is then **rolled back**, so every
task runs against the original seed dataset.

### Query parameter values

| Task | Parameter | Value |
|---|---|---|
| 3.1 | email, new phone | `arman.armanov@example.com`, `+77773414141` |
| 3.2 | city with +7 days | `Astana` (others +3 days) |
| 4.1 | corresponding author email | `amina.aminova@example.com` |
| 4.2 | city | `Astana` |
| 5.2 | pattern (ILIKE) | `%machine learning%` |
| 5.3 | paper_id | `1` |
| 5.4 | conference_id, expertise, min years | `1`, `Databases`, `3` |

Expected effects on the seed data: 3.1 updates 1 row; 3.2 updates 3 rows (Astana +7, Berlin and
Almaty +3); 4.1 deletes papers 6 and 7 (paper 12 is withdrawn but Amina is not its corresponding
author, so it is kept) together with 3 authorship, 3 keyword, 3 version and 2 review rows; 4.2
deletes session 3 (empty, Astana) and keeps session 5 (empty, Berlin); 5.4 returns reviewers 4, 5
and 6; 6.4 returns reviewers 4, 5 and 6 (average 2.125 reviews per reviewer, counting reviewer
10 with zero reviews); 7 returns 80.00, 50.00 and NULL.

## Running the web application

```bash
python app.py                 # development server on http://localhost:5000
gunicorn app:app              # production
```

On start-up the application creates and seeds the schema if the database is empty.

Pages: Users, Papers, Reviews, Sessions (full CRUD), Conferences & tracks (read-only, including
host institutions and reviewer pools) and Schedule (queries the `accepted_paper_schedule` view).

- **Users**: create/edit/delete users; author profile (ORCID, research areas) and reviewer
  profile (years of experience, expertise areas) are managed in the same form.
- **Papers**: create/edit/delete papers; authors (ordered, with one corresponding author),
  keywords and session are edited in the paper form; versions are added and deleted on the paper
  page.
- **Reviews**: create/edit/delete completed reviews.
- **Sessions**: create/edit/delete sessions; assign and unassign papers on the session page.

Each change runs in a single transaction. Failed operations are rolled back and reported at the
top of the page with the reason (application check or violated database constraint).

### Deployment

The repository includes a Render Blueprint (`render.yaml`) that creates a free PostgreSQL
database and the web service (`gunicorn app:app`, `DATABASE_URL` wired from the database). In
Render: *New → Blueprint →* select the repository → *Apply*. The schema and seed data are
created automatically on first start. Any other host works by setting `DATABASE_URL` (both
`postgres://` and `postgresql://` URLs are accepted) and running `gunicorn app:app`.

Render's free PostgreSQL instances expire after 30 days; for grading beyond that, use a
persistent free database such as Neon or Supabase and set its URL as `DATABASE_URL`.

## Schema, keys and references

Primary keys are underlined in the reference schema notation as **bold** here.

| Table | Columns | Keys / constraints |
|---|---|---|
| app_user | **user_id**, given_name, surname, email, affiliation, country, phone_number | UNIQUE(email); all NOT NULL |
| author | **author_id**, orcid (optional) | author_id → app_user ON DELETE CASCADE; UNIQUE(orcid) |
| author_research_area | **author_id, area_label** | author_id → author ON DELETE CASCADE |
| reviewer | **reviewer_id**, years_experience | reviewer_id → app_user ON DELETE CASCADE; CHECK years_experience ≥ 0 |
| reviewer_expertise | **reviewer_id, area_label** | reviewer_id → reviewer ON DELETE CASCADE |
| conference | **conference_id**, name, acronym, description, city, country, start_date, end_date, submission_deadline, review_deadline | CHECK end_date ≥ start_date |
| conference_host | **conference_id, host_name** | conference_id → conference ON DELETE CASCADE |
| conference_reviewer | **conference_id, reviewer_id** | → conference ON DELETE CASCADE; → reviewer ON DELETE CASCADE |
| track | **track_id**, conference_id, name, description, research_area, coordinator_id | conference_id → conference ON DELETE CASCADE; coordinator_id → reviewer ON DELETE RESTRICT |
| conference_session | **session_id**, conference_id, title, session_date, start_time, end_time, room_label, chair_id | conference_id → conference ON DELETE CASCADE; chair_id → reviewer ON DELETE RESTRICT; CHECK end_time > start_time |
| paper | **paper_id**, track_id, title, abstract, submission_date, status, session_id (optional) | track_id → track ON DELETE RESTRICT; session_id → conference_session ON DELETE SET NULL; CHECK status IN (submitted, under review, accepted, rejected, withdrawn) |
| paper_keyword | **paper_id, keyword** | paper_id → paper ON DELETE CASCADE |
| paper_author | **paper_id, author_id**, author_position, is_corresponding | paper_id → paper ON DELETE CASCADE; author_id → author ON DELETE RESTRICT; UNIQUE(paper_id, author_position); CHECK author_position > 0 |
| paper_version | **paper_id, version_no**, file_location, uploaded_at, change_note (optional) | paper_id → paper ON DELETE CASCADE; CHECK version_no > 0 |
| review | **review_id**, paper_id, reviewer_id, overall_score, recommendation, comments_for_authors, confidential_comments (optional), review_submission_date | paper_id → paper ON DELETE CASCADE; reviewer_id → reviewer ON DELETE RESTRICT; UNIQUE(paper_id, reviewer_id); CHECK overall_score BETWEEN 1 AND 5; CHECK recommendation IN (accept, reject) |

All columns not marked optional are `NOT NULL`. Surrogate keys use
`GENERATED BY DEFAULT AS IDENTITY`. Multivalued labels (research areas, expertise areas,
keywords, host institutions) are stored in their own relations, never as comma-separated text.

View: `accepted_paper_schedule` – one row per paper assigned to a session (inner join on
`paper.session_id`), with paper, conference, track, session, chair and corresponding author.

### Deletion behaviour

- Deleting a **paper** cascades to its versions (required), authorship, keywords and reviews.
- Deleting a **session** sets `paper.session_id` to NULL (papers become unscheduled).
- Deleting a **conference** cascades to its hosts, reviewer-pool memberships, tracks and
  sessions; it is rejected while any of its tracks has papers (`paper.track_id` RESTRICT). User
  and reviewer records are never deleted.
- Deleting a **user** cascades to the author/reviewer profile and its labels and pool
  memberships; it is rejected while the user still authors a paper, has written a review, or
  coordinates a track / chairs a session (RESTRICT). Removing a role in the user form follows the
  same rules.

## Required checks

Database constraints (Part 1): all keys, foreign keys, NOT NULL, unique email, unique author
position per paper, one review per reviewer and paper, and the CHECK constraints listed above.
Only completed reviews are stored: every review field except confidential comments is NOT NULL.

Application checks (in `app.py`, executed inside the same transaction as the change):

1. **No self-reviews** – `check_no_self_review` rejects creating or editing a review whose
   reviewer is an author of the paper; `check_authors_have_not_reviewed` rejects changing a
   paper's authors to include someone who has reviewed it.
2. **Valid session assignments** – `check_session_assignment` rejects a scheduled paper that is
   not accepted or whose track belongs to a different conference than the session. It runs when
   a paper is created/edited (status, track or session change) and when a paper is assigned on
   the session page. Editing a session's conference is rejected while it has assigned papers
   from another conference.

Demonstration: reviewing paper 3 as Arman Armanov (reviewer 1, author of paper 3) is rejected;
assigning paper 9 (under review) or paper 4 (CADS) to session 4 (EMLS) is rejected.

## Other business rules

All Assignment 1 rules hold in the sample data. Enforcement:

| Rule | Enforced? |
|---|---|
| Every user is an author, a reviewer, or both | Yes – user form |
| Authors have ≥ 1 research area; reviewers ≥ 1 expertise area | Yes – user form |
| Paper has ≥ 1 author, ≥ 1 keyword | Yes – paper form |
| Exactly one corresponding author per paper | Yes – paper form |
| Paper has ≥ 1 version | Yes – version 1 required on creation; last version cannot be deleted |
| Conference has ≥ 1 host, ≥ 1 track, ≥ 1 pool reviewer | Data only (conferences are read-only) |
| Track coordinator / session chair belongs to the conference's reviewer pool | Data only |
| Highest version number is the current version | By definition (queries order by version_no) |

## Design assumptions and changes from Assignment 1

- The schema follows the reference schema in Appendix A. Author/reviewer are an overlapping,
  total specialization of user, mapped to one table per subclass sharing the user key.
- Reviews of a deleted paper are deleted with it (needed for task 4.1); reviews are kept when a
  reviewer is involved elsewhere, so a reviewer with reviews cannot be deleted.
- Version numbers may have gaps (paper 9 has versions 1 and 3).
- Label matching is exact (5.4 matches the expertise label `Databases`, not
  `Distributed Databases`); 5.2 uses case-insensitive `ILIKE`.
- ORCID is optional but unique when present.

## Sample data overview

12 users (author-only: 2, 7, 8, 11; reviewer-only: 4, 5, 6, 10, 12; both: 1, 3, 9), 3
conferences (CADS 2026 in Astana, EMLS 2026 in Berlin, KSEW 2026 in Almaty with no papers), 6
tracks (tracks 3 and 6 empty), 5 sessions (3 in Astana and 5 in Berlin are empty), 12 papers
covering all five statuses (accepted papers 1, 2, 3, 8 are scheduled, paper 4 is not), 17
versions, 17 reviews (review counts per reviewer 5, 3, 3, 2, 2, 1, 1, 0; reviewer 10 has none).
