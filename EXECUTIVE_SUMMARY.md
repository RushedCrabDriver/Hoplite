# Executive Summary – CSCI 341 Assignment 3

**Team members**

| Name | Student ID | Contribution |
|---|---|---|
| _Sanzhar Mailebayev_ | _ID_ | _e.g. schema and sample data_ |
| _Sanzhar Mailebayev_ | _ID_ | _e.g. Part 2 queries_ |
| _Sanzhar Mailebayev_ | _ID_ | _e.g. web application and deployment_ |

**Completed work**

- **Part 1 – Relational database and sample data.** PostgreSQL schema with 15 tables derived
  from the Assignment 1 model: primary keys, foreign keys with documented deletion actions,
  NOT NULL, unique email, unique author position per paper, one review per reviewer and paper,
  and CHECK constraints for paper status, review score (1–5), recommendation, author position,
  version number, reviewing experience, conference dates and session times. Multivalued labels
  are stored in separate relations. Repeatable creation and seeding via `setup_db.py` or the
  `pg_dump` export. Sample data: 12 users, 3 conferences, 12 papers, 17 versions, 17 reviews,
  covering every case required by the assignment.
- **Part 2 – SQL operations through Python and SQLAlchemy.** `part2_queries.py` creates and
  seeds the database, then runs tasks 3.1–8 with bound parameters, printing each SQL statement
  and result; updates and deletions show before/after results and are rolled back. Includes the
  `accepted_paper_schedule` view. Full output is in `part2_output.txt`.
- **Part 3 – Web application.** Flask application with full CRUD for users (with author and
  reviewer profiles), papers (with authors, keywords and versions), reviews and sessions;
  read-only pages for conferences, tracks, reviewer pools and the schedule view. Every change runs
  in one transaction; failures are reported with the reason. Both required application checks
  (self-review prevention and session-assignment validation) are enforced.

**Incomplete or non-working requirements:** _None / list here._

**Links:** see `links.txt` (video and application URL).
