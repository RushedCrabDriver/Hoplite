"""CSCI 341 Assignment 3 - Part 2: SQL operations through Python and SQLAlchemy.

Every operation is executed with SQLAlchemy text() and bound parameters.
Items 1-2 (re)create and seed the database. Every later update/delete runs inside a
transaction that is rolled back, so each task runs against the original seed dataset.

Usage:  python part2_queries.py > part2_output.txt
"""
from sqlalchemy import text

from db import TABLES, create_schema, get_engine, read_sql, seed_data

# Query parameter values (documented in README).
PARAMS = {
    "arman_email": "arman.armanov@example.com",
    "arman_phone": "+77773414141",
    "amina_email": "amina.aminova@example.com",
    "astana": "Astana",
    "paper_id_5_3": 1,
    "conference_id_5_4": 1,
    "expertise_5_4": "Databases",
    "min_years_5_4": 3,
    "ml_pattern_5_2": "%machine learning%",
}

engine = get_engine()


# ---------------------------------------------------------------- output helpers
def banner(title: str) -> None:
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def show_sql(sql: str, params: dict | None = None) -> None:
    print("SQL:")
    for line in sql.strip().splitlines():
        print("    " + line)
    if params:
        print(f"Parameters: {params}")


def print_result(result) -> None:
    cols = list(result.keys())
    rows = [tuple("NULL" if v is None else str(v) for v in r) for r in result.fetchall()]
    widths = [max([len(c)] + [len(r[i]) for r in rows]) for i, c in enumerate(cols)]
    line = " | ".join(c.ljust(w) for c, w in zip(cols, widths))
    print(line)
    print("-+-".join("-" * w for w in widths))
    for r in rows:
        print(" | ".join(v.ljust(w) for v, w in zip(r, widths)))
    print(f"({len(rows)} row{'s' if len(rows) != 1 else ''})")


def run_query(conn, label: str, sql: str, params: dict | None = None) -> None:
    print(f"\n-- {label}")
    show_sql(sql, params)
    print("Result:")
    print_result(conn.execute(text(sql), params or {}))


def run_mutation(conn, sql: str, params: dict | None = None) -> None:
    print("\n-- Statement")
    show_sql(sql, params)
    result = conn.execute(text(sql), params or {})
    print(f"Rows affected: {result.rowcount}")


# ---------------------------------------------------------------- 1 and 2
def task_1_and_2() -> None:
    banner("Task 1: Create statements (sql/schema.sql + sql/view.sql)")
    print(read_sql("schema.sql"))
    with engine.begin() as conn:
        create_schema(conn)
    print("Schema created.")

    banner("Task 2: Insert statements (sql/seed.sql) and row counts")
    with engine.begin() as conn:
        seed_data(conn)
    print("Seed data inserted from sql/seed.sql.")
    with engine.connect() as conn:
        union = "\nUNION ALL ".join(
            f"SELECT '{t}' AS table_name, COUNT(*) AS row_count FROM {t}" for t in TABLES
        )
        run_query(conn, "Row count of every table", union)


# ---------------------------------------------------------------- 3 updates
def task_3_1() -> None:
    banner("Task 3.1: Update Arman Armanov's phone number (identified by email)")
    select_sql = """
SELECT user_id, given_name, surname, email, phone_number
FROM app_user
WHERE email = :email"""
    update_sql = """
UPDATE app_user
SET phone_number = :phone
WHERE email = :email"""
    p = {"email": PARAMS["arman_email"]}
    with engine.connect() as conn:
        trans = conn.begin()
        run_query(conn, "Before", select_sql, p)
        run_mutation(conn, update_sql, {"phone": PARAMS["arman_phone"], **p})
        run_query(conn, "After", select_sql, p)
        trans.rollback()
        print("\nTransaction rolled back (seed data restored).")


def task_3_2() -> None:
    banner("Task 3.2: Conditional review deadline extension (+7 days Astana, +3 days otherwise)")
    select_sql = """
SELECT conference_id, acronym, city, review_deadline
FROM conference
ORDER BY conference_id"""
    update_sql = """
UPDATE conference
SET review_deadline = review_deadline +
    CASE WHEN city = :city THEN 7 ELSE 3 END"""
    with engine.connect() as conn:
        trans = conn.begin()
        run_query(conn, "Before", select_sql)
        run_mutation(conn, update_sql, {"city": PARAMS["astana"]})
        run_query(conn, "After", select_sql)
        trans.rollback()
        print("\nTransaction rolled back (seed data restored).")


# ---------------------------------------------------------------- 4 deletes
def task_4_1() -> None:
    banner("Task 4.1: Delete withdrawn papers whose corresponding author is Amina Aminova")
    p = {"email": PARAMS["amina_email"]}
    papers_sql = """
SELECT p.paper_id, p.title, p.status,
       u.email AS corresponding_author_email
FROM paper p
JOIN paper_author pa ON pa.paper_id = p.paper_id AND pa.is_corresponding
JOIN app_user u ON u.user_id = pa.author_id
ORDER BY p.paper_id"""
    dependents_sql = """
SELECT (SELECT COUNT(*) FROM paper)         AS papers,
       (SELECT COUNT(*) FROM paper_author)  AS authorships,
       (SELECT COUNT(*) FROM paper_keyword) AS keywords,
       (SELECT COUNT(*) FROM paper_version) AS versions,
       (SELECT COUNT(*) FROM review)        AS reviews,
       (SELECT COUNT(*) FROM app_user)      AS users,
       (SELECT COUNT(*) FROM track)         AS tracks,
       (SELECT COUNT(*) FROM conference)    AS conferences"""
    delete_sql = """
DELETE FROM paper
WHERE status = 'withdrawn'
  AND paper_id IN (
        SELECT pa.paper_id
        FROM paper_author pa
        JOIN app_user u ON u.user_id = pa.author_id
        WHERE pa.is_corresponding
          AND u.email = :email)"""
    with engine.connect() as conn:
        trans = conn.begin()
        run_query(conn, "Before: papers with corresponding author", papers_sql)
        run_query(conn, "Before: related row counts", dependents_sql)
        print("\nAuthorship, keyword, version and review rows are removed by ON DELETE CASCADE.")
        run_mutation(conn, delete_sql, p)
        run_query(conn, "After: papers with corresponding author", papers_sql)
        run_query(conn, "After: related row counts", dependents_sql)
        trans.rollback()
        print("\nTransaction rolled back (seed data restored).")


def task_4_2() -> None:
    banner("Task 4.2: Delete empty sessions of conferences held in Astana")
    select_sql = """
SELECT s.session_id, s.title, c.conference_id, c.city,
       COUNT(p.paper_id) AS assigned_papers
FROM conference_session s
JOIN conference c ON c.conference_id = s.conference_id
LEFT JOIN paper p ON p.session_id = s.session_id
GROUP BY s.session_id, s.title, c.conference_id, c.city
ORDER BY s.session_id"""
    delete_sql = """
DELETE FROM conference_session s
USING conference c
WHERE c.conference_id = s.conference_id
  AND c.city = :city
  AND NOT EXISTS (SELECT 1 FROM paper p WHERE p.session_id = s.session_id)"""
    with engine.connect() as conn:
        trans = conn.begin()
        run_query(conn, "Before", select_sql)
        run_mutation(conn, delete_sql, {"city": PARAMS["astana"]})
        run_query(conn, "After", select_sql)
        run_query(conn, "After: conferences are kept",
                  "SELECT conference_id, acronym, city FROM conference ORDER BY conference_id")
        trans.rollback()
        print("\nTransaction rolled back (seed data restored).")


# ---------------------------------------------------------------- 5 simple queries
def task_5() -> None:
    with engine.connect() as conn:
        banner("Task 5.1: Accepted papers with corresponding author, track and conference")
        run_query(conn, "5.1", """
SELECT p.paper_id, p.title,
       u.given_name || ' ' || u.surname AS corresponding_author,
       u.email AS corresponding_email,
       t.name AS track_name,
       c.conference_id, c.acronym
FROM paper p
JOIN track t ON t.track_id = p.track_id
JOIN conference c ON c.conference_id = t.conference_id
JOIN paper_author pa ON pa.paper_id = p.paper_id AND pa.is_corresponding
JOIN app_user u ON u.user_id = pa.author_id
WHERE p.status = 'accepted'
ORDER BY p.paper_id""")

        banner("Task 5.2: Papers whose abstract contains 'machine learning' (case-insensitive)")
        run_query(conn, "5.2", """
SELECT paper_id, title
FROM paper
WHERE abstract ILIKE :pattern
ORDER BY paper_id""", {"pattern": PARAMS["ml_pattern_5_2"]})

        banner("Task 5.3: Versions of a selected paper, newest first")
        run_query(conn, "5.3", """
SELECT version_no, file_location, uploaded_at
FROM paper_version
WHERE paper_id = :paper_id
ORDER BY version_no DESC""", {"paper_id": PARAMS["paper_id_5_3"]})

        banner("Task 5.4: Pool reviewers of a conference with Databases expertise and >= 3 years")
        run_query(conn, "5.4", """
SELECT r.reviewer_id, u.given_name || ' ' || u.surname AS full_name, u.email
FROM reviewer r
JOIN app_user u ON u.user_id = r.reviewer_id
JOIN conference_reviewer cr ON cr.reviewer_id = r.reviewer_id
WHERE cr.conference_id = :conference_id
  AND r.years_experience >= :min_years
  AND EXISTS (SELECT 1 FROM reviewer_expertise e
              WHERE e.reviewer_id = r.reviewer_id AND e.area_label = :expertise)
ORDER BY r.reviewer_id""", {
            "conference_id": PARAMS["conference_id_5_4"],
            "min_years": PARAMS["min_years_5_4"],
            "expertise": PARAMS["expertise_5_4"],
        })


# ---------------------------------------------------------------- 6 complex queries
def task_6() -> None:
    with engine.connect() as conn:
        banner("Task 6.1: Papers and distinct authors per track (including empty tracks)")
        run_query(conn, "6.1", """
SELECT t.track_id, t.name AS track_name, t.conference_id,
       COUNT(DISTINCT p.paper_id)   AS paper_count,
       COUNT(DISTINCT pa.author_id) AS author_count
FROM track t
LEFT JOIN paper p         ON p.track_id = t.track_id
LEFT JOIN paper_author pa ON pa.paper_id = p.paper_id
GROUP BY t.track_id, t.name, t.conference_id
ORDER BY t.track_id""")

        banner("Task 6.2: Review count and average score per reviewer (including zero reviews)")
        run_query(conn, "6.2", """
SELECT r.reviewer_id,
       u.given_name || ' ' || u.surname AS full_name,
       COUNT(rv.review_id)               AS review_count,
       ROUND(AVG(rv.overall_score), 2)   AS avg_score
FROM reviewer r
JOIN app_user u     ON u.user_id = r.reviewer_id
LEFT JOIN review rv ON rv.reviewer_id = r.reviewer_id
GROUP BY r.reviewer_id, u.given_name, u.surname
ORDER BY r.reviewer_id""")

        banner("Task 6.3: Papers, accepted papers and average review score per conference")
        run_query(conn, "6.3", """
WITH paper_stats AS (
    SELECT t.conference_id,
           COUNT(*)                                     AS total_papers,
           COUNT(*) FILTER (WHERE p.status = 'accepted') AS accepted_papers
    FROM paper p
    JOIN track t ON t.track_id = p.track_id
    GROUP BY t.conference_id
), review_stats AS (
    SELECT t.conference_id, AVG(rv.overall_score) AS avg_score
    FROM review rv
    JOIN paper p ON p.paper_id = rv.paper_id
    JOIN track t ON t.track_id = p.track_id
    GROUP BY t.conference_id
)
SELECT c.conference_id, c.acronym,
       COALESCE(ps.total_papers, 0)    AS total_papers,
       COALESCE(ps.accepted_papers, 0) AS accepted_papers,
       ROUND(rs.avg_score, 2)          AS avg_review_score
FROM conference c
LEFT JOIN paper_stats ps  ON ps.conference_id = c.conference_id
LEFT JOIN review_stats rs ON rs.conference_id = c.conference_id
ORDER BY c.conference_id""")

        banner("Task 6.4: Reviewers with more reviews than the average per reviewer")
        run_query(conn, "6.4", """
WITH review_counts AS (
    SELECT r.reviewer_id, COUNT(rv.review_id) AS review_count
    FROM reviewer r
    LEFT JOIN review rv ON rv.reviewer_id = r.reviewer_id
    GROUP BY r.reviewer_id
), overall AS (
    SELECT AVG(review_count) AS avg_reviews FROM review_counts
)
SELECT rc.reviewer_id,
       u.given_name || ' ' || u.surname AS full_name,
       rc.review_count,
       ROUND(o.avg_reviews, 3) AS overall_avg_reviews
FROM review_counts rc
JOIN app_user u ON u.user_id = rc.reviewer_id
CROSS JOIN overall o
WHERE rc.review_count > o.avg_reviews
ORDER BY rc.review_count DESC, rc.reviewer_id""")


# ---------------------------------------------------------------- 7 derived attribute
def task_7() -> None:
    banner("Task 7: Acceptance rate per conference (derived attribute)")
    with engine.connect() as conn:
        run_query(conn, "7", """
SELECT c.conference_id, c.acronym,
       COUNT(p.paper_id) FILTER (WHERE p.status = 'accepted') AS accepted_count,
       COUNT(p.paper_id) FILTER (WHERE p.status = 'rejected') AS rejected_count,
       ROUND(100.0 * COUNT(p.paper_id) FILTER (WHERE p.status = 'accepted')
             / NULLIF(COUNT(p.paper_id) FILTER (WHERE p.status IN ('accepted', 'rejected')), 0),
             2) AS acceptance_rate
FROM conference c
LEFT JOIN track t ON t.conference_id = c.conference_id
LEFT JOIN paper p ON p.track_id = t.track_id
GROUP BY c.conference_id, c.acronym
ORDER BY c.conference_id""")


# ---------------------------------------------------------------- 8 view
def task_8() -> None:
    banner("Task 8: View accepted_paper_schedule")
    view_sql = read_sql("view.sql")
    with engine.begin() as conn:
        show_sql(view_sql)
        conn.exec_driver_sql(view_sql)
        print("View created (CREATE OR REPLACE VIEW).")
    with engine.connect() as conn:
        run_query(conn, "Query the view", """
SELECT *
FROM accepted_paper_schedule
ORDER BY conference_id, session_date, start_time, session_id, paper_id""")


def main() -> None:
    task_1_and_2()
    task_3_1()
    task_3_2()
    task_4_1()
    task_4_2()
    task_5()
    task_6()
    task_7()
    task_8()


if __name__ == "__main__":
    main()
