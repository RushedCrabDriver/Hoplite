"""CSCI 341 Assignment 3 - Part 3: web application (Flask + SQLAlchemy Core/text()).

CRUD for users (with author/reviewer profiles), papers (with authors, keywords and
versions), reviews and sessions. Conferences, tracks and reviewer pools are read-only.
"""
import os
from datetime import datetime

from flask import Flask, abort, flash, redirect, render_template, request, url_for
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from db import create_schema, get_engine, seed_data

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
engine = get_engine()

STATUSES = ["submitted", "under review", "accepted", "rejected", "withdrawn"]
AUTHOR_SLOTS = 6


class ValidationError(Exception):
    """Raised by application checks; the surrounding transaction is rolled back."""


# ------------------------------------------------------------------ helpers
def rows(conn, sql, **params):
    return conn.execute(text(sql), params).mappings().all()


def one(conn, sql, **params):
    return conn.execute(text(sql), params).mappings().first()


def blank_to_none(value):
    value = (value or "").strip()
    return value or None


def split_labels(raw):
    """Comma- or newline-separated labels -> unique, ordered list."""
    seen = []
    for part in (raw or "").replace("\n", ",").split(","):
        part = part.strip()
        if part and part not in seen:
            seen.append(part)
    return seen


def db_error_message(exc: DBAPIError) -> str:
    diag = getattr(exc.orig, "diag", None)
    if diag is None:
        return f"Database error: {exc.orig}"
    msg = f"Database rejected the change: {diag.message_primary}"
    if diag.message_detail:
        msg += f" {diag.message_detail}"
    return msg


def run_tx(work, success_message):
    """Execute work(conn) in one transaction; report failures instead of raising."""
    try:
        with engine.begin() as conn:
            result = work(conn)
        flash(success_message, "success")
        return True, result
    except ValidationError as exc:
        flash(f"Rejected: {exc}", "error")
    except DBAPIError as exc:
        flash(db_error_message(exc), "error")
    return False, None


def ensure_database():
    """Create and seed the schema on first start (empty database)."""
    with engine.begin() as conn:
        exists = conn.execute(text("SELECT to_regclass('public.app_user')")).scalar()
        if exists is None:
            create_schema(conn)
            seed_data(conn)


# ------------------------------------------------------------------ application checks
def check_no_self_review(conn, paper_id, reviewer_ids):
    """Check 1: a reviewer may not review a paper they authored."""
    if not reviewer_ids:
        return
    clash = one(conn, """
        SELECT u.given_name || ' ' || u.surname AS name
        FROM paper_author pa JOIN app_user u ON u.user_id = pa.author_id
        WHERE pa.paper_id = :pid AND pa.author_id = ANY(:ids)
        LIMIT 1""", pid=paper_id, ids=list(reviewer_ids))
    if clash:
        raise ValidationError(
            f"self-review: {clash['name']} is an author of paper {paper_id} "
            "and cannot review it.")


def check_authors_have_not_reviewed(conn, paper_id, author_ids):
    """Check 1 (author change side): new authors must not have reviewed the paper."""
    clash = one(conn, """
        SELECT u.given_name || ' ' || u.surname AS name
        FROM review r JOIN app_user u ON u.user_id = r.reviewer_id
        WHERE r.paper_id = :pid AND r.reviewer_id = ANY(:ids)
        LIMIT 1""", pid=paper_id, ids=list(author_ids))
    if clash:
        raise ValidationError(
            f"self-review: {clash['name']} has reviewed paper {paper_id} "
            "and cannot be added as its author.")


def check_session_assignment(conn, status, track_id, session_id):
    """Check 2: a scheduled paper must be accepted and in the session's conference."""
    if session_id is None:
        return
    if status != "accepted":
        raise ValidationError(
            f"invalid session assignment: only accepted papers can be scheduled "
            f"(paper status is '{status}').")
    info = one(conn, """
        SELECT t.conference_id AS track_conf, s.conference_id AS session_conf
        FROM track t, conference_session s
        WHERE t.track_id = :tid AND s.session_id = :sid""", tid=track_id, sid=session_id)
    if info is None:
        raise ValidationError("unknown track or session.")
    if info["track_conf"] != info["session_conf"]:
        raise ValidationError(
            f"invalid session assignment: the paper's track belongs to conference "
            f"{info['track_conf']} but session {session_id} belongs to conference "
            f"{info['session_conf']}.")


# ------------------------------------------------------------------ home / reference data
@app.route("/")
def index():
    with engine.connect() as conn:
        counts = one(conn, """
            SELECT (SELECT COUNT(*) FROM app_user) AS users,
                   (SELECT COUNT(*) FROM paper) AS papers,
                   (SELECT COUNT(*) FROM review) AS reviews,
                   (SELECT COUNT(*) FROM conference_session) AS sessions,
                   (SELECT COUNT(*) FROM conference) AS conferences""")
    return render_template("index.html", counts=counts)


@app.route("/conferences")
def conferences():
    with engine.connect() as conn:
        confs = rows(conn, """
            SELECT c.*,
                   (SELECT string_agg(host_name, ', ' ORDER BY host_name)
                    FROM conference_host h WHERE h.conference_id = c.conference_id) AS hosts,
                   (SELECT string_agg(u.given_name || ' ' || u.surname, ', ' ORDER BY u.user_id)
                    FROM conference_reviewer cr JOIN app_user u ON u.user_id = cr.reviewer_id
                    WHERE cr.conference_id = c.conference_id) AS pool
            FROM conference c ORDER BY c.conference_id""")
        tracks = rows(conn, """
            SELECT t.*, u.given_name || ' ' || u.surname AS coordinator,
                   (SELECT COUNT(*) FROM paper p WHERE p.track_id = t.track_id) AS papers
            FROM track t JOIN app_user u ON u.user_id = t.coordinator_id
            ORDER BY t.track_id""")
    return render_template("conferences.html", confs=confs, tracks=tracks)


@app.route("/schedule")
def schedule():
    with engine.connect() as conn:
        items = rows(conn, """
            SELECT * FROM accepted_paper_schedule
            ORDER BY conference_id, session_date, start_time, session_id, paper_id""")
    return render_template("schedule.html", items=items)


# ------------------------------------------------------------------ users
def load_user_form():
    f = request.form
    data = {
        "given_name": f.get("given_name", "").strip(),
        "surname": f.get("surname", "").strip(),
        "email": f.get("email", "").strip(),
        "affiliation": f.get("affiliation", "").strip(),
        "country": f.get("country", "").strip(),
        "phone_number": f.get("phone_number", "").strip(),
        "is_author": f.get("is_author") == "on",
        "orcid": blank_to_none(f.get("orcid")),
        "research_areas": split_labels(f.get("research_areas")),
        "is_reviewer": f.get("is_reviewer") == "on",
        "years_experience": f.get("years_experience", "").strip(),
        "expertise_areas": split_labels(f.get("expertise_areas")),
    }
    return data


def validate_user(d):
    for key in ("given_name", "surname", "email", "affiliation", "country", "phone_number"):
        if not d[key]:
            raise ValidationError(f"{key.replace('_', ' ')} is required.")
    if not (d["is_author"] or d["is_reviewer"]):
        raise ValidationError("a user must be an author, a reviewer, or both.")
    if d["is_author"] and not d["research_areas"]:
        raise ValidationError("authors need at least one research area.")
    if d["is_reviewer"]:
        if not d["expertise_areas"]:
            raise ValidationError("reviewers need at least one expertise area.")
        try:
            d["years_experience"] = int(d["years_experience"])
        except ValueError:
            raise ValidationError("years of experience must be an integer.")


def save_roles(conn, uid, d):
    if d["is_author"]:
        conn.execute(text("""
            INSERT INTO author (author_id, orcid) VALUES (:id, :orcid)
            ON CONFLICT (author_id) DO UPDATE SET orcid = EXCLUDED.orcid"""),
            {"id": uid, "orcid": d["orcid"]})
        conn.execute(text("DELETE FROM author_research_area WHERE author_id = :id"), {"id": uid})
        for label in d["research_areas"]:
            conn.execute(text("INSERT INTO author_research_area VALUES (:id, :l)"),
                         {"id": uid, "l": label})
    else:
        conn.execute(text("DELETE FROM author WHERE author_id = :id"), {"id": uid})

    if d["is_reviewer"]:
        conn.execute(text("""
            INSERT INTO reviewer (reviewer_id, years_experience) VALUES (:id, :y)
            ON CONFLICT (reviewer_id) DO UPDATE SET years_experience = EXCLUDED.years_experience"""),
            {"id": uid, "y": d["years_experience"]})
        conn.execute(text("DELETE FROM reviewer_expertise WHERE reviewer_id = :id"), {"id": uid})
        for label in d["expertise_areas"]:
            conn.execute(text("INSERT INTO reviewer_expertise VALUES (:id, :l)"),
                         {"id": uid, "l": label})
    else:
        conn.execute(text("DELETE FROM reviewer WHERE reviewer_id = :id"), {"id": uid})


def get_user(conn, uid):
    user = one(conn, """
        SELECT u.*, a.author_id IS NOT NULL AS is_author, a.orcid,
               r.reviewer_id IS NOT NULL AS is_reviewer, r.years_experience,
               (SELECT string_agg(area_label, ', ' ORDER BY area_label)
                FROM author_research_area WHERE author_id = u.user_id) AS research_areas,
               (SELECT string_agg(area_label, ', ' ORDER BY area_label)
                FROM reviewer_expertise WHERE reviewer_id = u.user_id) AS expertise_areas
        FROM app_user u
        LEFT JOIN author a ON a.author_id = u.user_id
        LEFT JOIN reviewer r ON r.reviewer_id = u.user_id
        WHERE u.user_id = :id""", id=uid)
    if user is None:
        abort(404)
    return user


@app.route("/users")
def users():
    with engine.connect() as conn:
        items = rows(conn, """
            SELECT u.user_id, u.given_name, u.surname, u.email, u.affiliation, u.country,
                   EXISTS (SELECT 1 FROM author a WHERE a.author_id = u.user_id) AS is_author,
                   EXISTS (SELECT 1 FROM reviewer r WHERE r.reviewer_id = u.user_id) AS is_reviewer
            FROM app_user u ORDER BY u.user_id""")
    return render_template("users.html", items=items)


@app.route("/users/<int:uid>")
def user_detail(uid):
    with engine.connect() as conn:
        user = get_user(conn, uid)
        papers = rows(conn, """
            SELECT p.paper_id, p.title, p.status, pa.author_position, pa.is_corresponding
            FROM paper_author pa JOIN paper p ON p.paper_id = pa.paper_id
            WHERE pa.author_id = :id ORDER BY p.paper_id""", id=uid)
        reviews = rows(conn, """
            SELECT r.review_id, r.paper_id, p.title, r.overall_score, r.recommendation
            FROM review r JOIN paper p ON p.paper_id = r.paper_id
            WHERE r.reviewer_id = :id ORDER BY r.review_id""", id=uid)
        pools = rows(conn, """
            SELECT c.conference_id, c.acronym FROM conference_reviewer cr
            JOIN conference c ON c.conference_id = cr.conference_id
            WHERE cr.reviewer_id = :id ORDER BY c.conference_id""", id=uid)
    return render_template("user_detail.html", user=user, papers=papers,
                           reviews=reviews, pools=pools)


@app.route("/users/new", methods=["GET", "POST"])
def user_new():
    if request.method == "POST":
        d = load_user_form()

        def work(conn):
            validate_user(d)
            uid = conn.execute(text("""
                INSERT INTO app_user (given_name, surname, email, affiliation, country, phone_number)
                VALUES (:given_name, :surname, :email, :affiliation, :country, :phone_number)
                RETURNING user_id"""), d).scalar_one()
            save_roles(conn, uid, d)
            return uid

        ok, uid = run_tx(work, "User created.")
        if ok:
            return redirect(url_for("user_detail", uid=uid))
        return render_template("user_form.html", user=request.form, action="Create")
    return render_template("user_form.html", user={}, action="Create")


@app.route("/users/<int:uid>/edit", methods=["GET", "POST"])
def user_edit(uid):
    if request.method == "POST":
        d = load_user_form()

        def work(conn):
            validate_user(d)
            res = conn.execute(text("""
                UPDATE app_user SET given_name = :given_name, surname = :surname, email = :email,
                       affiliation = :affiliation, country = :country, phone_number = :phone_number
                WHERE user_id = :uid"""), {**d, "uid": uid})
            if res.rowcount == 0:
                raise ValidationError("user not found.")
            save_roles(conn, uid, d)

        ok, _ = run_tx(work, "User updated.")
        if ok:
            return redirect(url_for("user_detail", uid=uid))
        return render_template("user_form.html", user=request.form, action="Update", uid=uid)
    with engine.connect() as conn:
        user = dict(get_user(conn, uid))
    user["is_author"] = "on" if user["is_author"] else ""
    user["is_reviewer"] = "on" if user["is_reviewer"] else ""
    return render_template("user_form.html", user=user, action="Update", uid=uid)


@app.route("/users/<int:uid>/delete", methods=["POST"])
def user_delete(uid):
    def work(conn):
        if conn.execute(text("DELETE FROM app_user WHERE user_id = :id"), {"id": uid}).rowcount == 0:
            raise ValidationError("user not found.")

    ok, _ = run_tx(work, f"User {uid} deleted.")
    return redirect(url_for("users") if ok else url_for("user_detail", uid=uid))


# ------------------------------------------------------------------ papers
def paper_choices(conn):
    return {
        "tracks": rows(conn, """
            SELECT t.track_id, t.name, c.acronym, c.conference_id FROM track t
            JOIN conference c ON c.conference_id = t.conference_id ORDER BY t.track_id"""),
        "sessions": rows(conn, """
            SELECT s.session_id, s.title, c.acronym, c.conference_id FROM conference_session s
            JOIN conference c ON c.conference_id = s.conference_id ORDER BY s.session_id"""),
        "authors": rows(conn, """
            SELECT a.author_id, u.given_name || ' ' || u.surname AS name, u.email
            FROM author a JOIN app_user u ON u.user_id = a.author_id ORDER BY a.author_id"""),
        "statuses": STATUSES,
        "slots": range(AUTHOR_SLOTS),
    }


def load_paper_form():
    f = request.form
    authors = []
    for i in range(AUTHOR_SLOTS):
        value = f.get(f"author_{i}", "").strip()
        if value:
            authors.append((int(value), str(i) == f.get("corresponding")))
    session = f.get("session_id", "").strip()
    return {
        "track_id": int(f.get("track_id")) if f.get("track_id") else None,
        "title": f.get("title", "").strip(),
        "abstract": f.get("abstract", "").strip(),
        "submission_date": blank_to_none(f.get("submission_date")),
        "status": f.get("status", "submitted"),
        "session_id": int(session) if session else None,
        "keywords": split_labels(f.get("keywords")),
        "authors": authors,
        "file_location": blank_to_none(f.get("file_location")),
    }


def validate_paper(d, creating):
    if d["track_id"] is None or not d["title"] or not d["abstract"] or not d["submission_date"]:
        raise ValidationError("track, title, abstract and submission date are required.")
    if not d["keywords"]:
        raise ValidationError("at least one keyword is required.")
    if not d["authors"]:
        raise ValidationError("at least one author is required.")
    ids = [a for a, _ in d["authors"]]
    if len(set(ids)) != len(ids):
        raise ValidationError("the same author is listed more than once.")
    if sum(1 for _, corr in d["authors"] if corr) != 1:
        raise ValidationError("exactly one listed author must be the corresponding author.")
    if creating and not d["file_location"]:
        raise ValidationError("a file location for version 1 is required.")


def save_paper_children(conn, pid, d):
    conn.execute(text("DELETE FROM paper_author WHERE paper_id = :p"), {"p": pid})
    for position, (author_id, corr) in enumerate(d["authors"], start=1):
        conn.execute(text("""
            INSERT INTO paper_author (paper_id, author_id, author_position, is_corresponding)
            VALUES (:p, :a, :pos, :c)"""), {"p": pid, "a": author_id, "pos": position, "c": corr})
    conn.execute(text("DELETE FROM paper_keyword WHERE paper_id = :p"), {"p": pid})
    for kw in d["keywords"]:
        conn.execute(text("INSERT INTO paper_keyword (paper_id, keyword) VALUES (:p, :k)"),
                     {"p": pid, "k": kw})


@app.route("/papers")
def papers():
    with engine.connect() as conn:
        items = rows(conn, """
            SELECT p.paper_id, p.title, p.status, t.name AS track, c.acronym, p.session_id,
                   (SELECT u.given_name || ' ' || u.surname FROM paper_author pa
                    JOIN app_user u ON u.user_id = pa.author_id
                    WHERE pa.paper_id = p.paper_id AND pa.is_corresponding) AS corresponding,
                   (SELECT COUNT(*) FROM review r WHERE r.paper_id = p.paper_id) AS reviews
            FROM paper p JOIN track t ON t.track_id = p.track_id
            JOIN conference c ON c.conference_id = t.conference_id
            ORDER BY p.paper_id""")
    return render_template("papers.html", items=items)


@app.route("/papers/<int:pid>")
def paper_detail(pid):
    with engine.connect() as conn:
        paper = one(conn, """
            SELECT p.*, t.name AS track, c.conference_id, c.acronym,
                   s.title AS session_title,
                   (SELECT string_agg(keyword, ', ' ORDER BY keyword)
                    FROM paper_keyword k WHERE k.paper_id = p.paper_id) AS keywords
            FROM paper p JOIN track t ON t.track_id = p.track_id
            JOIN conference c ON c.conference_id = t.conference_id
            LEFT JOIN conference_session s ON s.session_id = p.session_id
            WHERE p.paper_id = :id""", id=pid)
        if paper is None:
            abort(404)
        authors = rows(conn, """
            SELECT pa.author_position, pa.is_corresponding, u.user_id,
                   u.given_name || ' ' || u.surname AS name, u.email
            FROM paper_author pa JOIN app_user u ON u.user_id = pa.author_id
            WHERE pa.paper_id = :id ORDER BY pa.author_position""", id=pid)
        versions = rows(conn, """
            SELECT * FROM paper_version WHERE paper_id = :id ORDER BY version_no DESC""", id=pid)
        reviews = rows(conn, """
            SELECT r.review_id, r.overall_score, r.recommendation,
                   u.given_name || ' ' || u.surname AS reviewer
            FROM review r JOIN app_user u ON u.user_id = r.reviewer_id
            WHERE r.paper_id = :id ORDER BY r.review_id""", id=pid)
    next_version = (versions[0]["version_no"] + 1) if versions else 1
    return render_template("paper_detail.html", paper=paper, authors=authors, versions=versions,
                           reviews=reviews, next_version=next_version,
                           now=datetime.now().strftime("%Y-%m-%dT%H:%M"))


def paper_form_values_from_request():
    values = dict(request.form)
    values["session_id"] = request.form.get("session_id", "")
    return values


@app.route("/papers/new", methods=["GET", "POST"])
def paper_new():
    if request.method == "POST":
        d = load_paper_form()

        def work(conn):
            validate_paper(d, creating=True)
            check_session_assignment(conn, d["status"], d["track_id"], d["session_id"])
            pid = conn.execute(text("""
                INSERT INTO paper (track_id, title, abstract, submission_date, status, session_id)
                VALUES (:track_id, :title, :abstract, :submission_date, :status, :session_id)
                RETURNING paper_id"""), d).scalar_one()
            save_paper_children(conn, pid, d)
            conn.execute(text("""
                INSERT INTO paper_version (paper_id, version_no, file_location, uploaded_at)
                VALUES (:p, 1, :f, now())"""), {"p": pid, "f": d["file_location"]})
            return pid

        ok, pid = run_tx(work, "Paper created.")
        if ok:
            return redirect(url_for("paper_detail", pid=pid))
        values = paper_form_values_from_request()
    else:
        values = {"status": "submitted", "submission_date": datetime.now().strftime("%Y-%m-%d")}
    with engine.connect() as conn:
        return render_template("paper_form.html", p=values, action="Create", **paper_choices(conn))


@app.route("/papers/<int:pid>/edit", methods=["GET", "POST"])
def paper_edit(pid):
    if request.method == "POST":
        d = load_paper_form()

        def work(conn):
            validate_paper(d, creating=False)
            check_session_assignment(conn, d["status"], d["track_id"], d["session_id"])
            check_authors_have_not_reviewed(conn, pid, [a for a, _ in d["authors"]])
            res = conn.execute(text("""
                UPDATE paper SET track_id = :track_id, title = :title, abstract = :abstract,
                       submission_date = :submission_date, status = :status, session_id = :session_id
                WHERE paper_id = :pid"""), {**d, "pid": pid})
            if res.rowcount == 0:
                raise ValidationError("paper not found.")
            save_paper_children(conn, pid, d)

        ok, _ = run_tx(work, "Paper updated.")
        if ok:
            return redirect(url_for("paper_detail", pid=pid))
        values = paper_form_values_from_request()
    else:
        with engine.connect() as conn:
            p = one(conn, "SELECT * FROM paper WHERE paper_id = :id", id=pid)
            if p is None:
                abort(404)
            values = {k: ("" if v is None else str(v)) for k, v in p.items()}
            values["keywords"] = ", ".join(r["keyword"] for r in rows(
                conn, "SELECT keyword FROM paper_keyword WHERE paper_id = :id ORDER BY keyword", id=pid))
            for i, a in enumerate(rows(conn, """
                    SELECT author_id, is_corresponding FROM paper_author
                    WHERE paper_id = :id ORDER BY author_position""", id=pid)):
                values[f"author_{i}"] = str(a["author_id"])
                if a["is_corresponding"]:
                    values["corresponding"] = str(i)
    with engine.connect() as conn:
        return render_template("paper_form.html", p=values, action="Update", pid=pid,
                               **paper_choices(conn))


@app.route("/papers/<int:pid>/delete", methods=["POST"])
def paper_delete(pid):
    def work(conn):
        if conn.execute(text("DELETE FROM paper WHERE paper_id = :id"), {"id": pid}).rowcount == 0:
            raise ValidationError("paper not found.")

    ok, _ = run_tx(work, f"Paper {pid} and its authorship, keywords, versions and reviews deleted.")
    return redirect(url_for("papers") if ok else url_for("paper_detail", pid=pid))


@app.route("/papers/<int:pid>/versions", methods=["POST"])
def version_add(pid):
    f = request.form

    def work(conn):
        try:
            version_no = int(f.get("version_no", ""))
        except ValueError:
            raise ValidationError("version number must be an integer.")
        if not f.get("file_location", "").strip() or not f.get("uploaded_at"):
            raise ValidationError("file location and upload time are required.")
        conn.execute(text("""
            INSERT INTO paper_version (paper_id, version_no, file_location, uploaded_at, change_note)
            VALUES (:p, :v, :f, :u, :n)"""), {
            "p": pid, "v": version_no, "f": f["file_location"].strip(),
            "u": f["uploaded_at"], "n": blank_to_none(f.get("change_note"))})

    run_tx(work, "Version added.")
    return redirect(url_for("paper_detail", pid=pid))


@app.route("/papers/<int:pid>/versions/<int:vno>/delete", methods=["POST"])
def version_delete(pid, vno):
    def work(conn):
        count = conn.execute(text("SELECT COUNT(*) FROM paper_version WHERE paper_id = :p"),
                             {"p": pid}).scalar_one()
        if count <= 1:
            raise ValidationError("a paper must keep at least one version.")
        conn.execute(text("DELETE FROM paper_version WHERE paper_id = :p AND version_no = :v"),
                     {"p": pid, "v": vno})

    run_tx(work, f"Version {vno} deleted.")
    return redirect(url_for("paper_detail", pid=pid))


# ------------------------------------------------------------------ reviews
def review_choices(conn):
    return {
        "papers": rows(conn, "SELECT paper_id, title FROM paper ORDER BY paper_id"),
        "reviewers": rows(conn, """
            SELECT r.reviewer_id, u.given_name || ' ' || u.surname AS name
            FROM reviewer r JOIN app_user u ON u.user_id = r.reviewer_id ORDER BY r.reviewer_id"""),
    }


def load_review_form():
    f = request.form
    try:
        d = {
            "paper_id": int(f.get("paper_id", "")),
            "reviewer_id": int(f.get("reviewer_id", "")),
            "overall_score": int(f.get("overall_score", "")),
        }
    except ValueError:
        raise ValidationError("paper, reviewer and an integer score are required.")
    d.update({
        "recommendation": f.get("recommendation", ""),
        "comments_for_authors": f.get("comments_for_authors", "").strip(),
        "confidential_comments": blank_to_none(f.get("confidential_comments")),
        "review_submission_date": blank_to_none(f.get("review_submission_date")),
    })
    if not d["comments_for_authors"] or not d["review_submission_date"]:
        raise ValidationError("only completed reviews are stored: comments for the authors "
                              "and a submission date are required.")
    return d


@app.route("/reviews")
def reviews():
    with engine.connect() as conn:
        items = rows(conn, """
            SELECT r.review_id, r.paper_id, p.title, r.reviewer_id,
                   u.given_name || ' ' || u.surname AS reviewer,
                   r.overall_score, r.recommendation, r.review_submission_date
            FROM review r JOIN paper p ON p.paper_id = r.paper_id
            JOIN app_user u ON u.user_id = r.reviewer_id ORDER BY r.review_id""")
    return render_template("reviews.html", items=items)


@app.route("/reviews/<int:rid>")
def review_detail(rid):
    with engine.connect() as conn:
        review = one(conn, """
            SELECT r.*, p.title, u.given_name || ' ' || u.surname AS reviewer
            FROM review r JOIN paper p ON p.paper_id = r.paper_id
            JOIN app_user u ON u.user_id = r.reviewer_id WHERE r.review_id = :id""", id=rid)
    if review is None:
        abort(404)
    return render_template("review_detail.html", r=review)


@app.route("/reviews/new", methods=["GET", "POST"])
def review_new():
    if request.method == "POST":
        def work(conn):
            d = load_review_form()
            check_no_self_review(conn, d["paper_id"], [d["reviewer_id"]])
            return conn.execute(text("""
                INSERT INTO review (paper_id, reviewer_id, overall_score, recommendation,
                    comments_for_authors, confidential_comments, review_submission_date)
                VALUES (:paper_id, :reviewer_id, :overall_score, :recommendation,
                    :comments_for_authors, :confidential_comments, :review_submission_date)
                RETURNING review_id"""), d).scalar_one()

        ok, rid = run_tx(work, "Review created.")
        if ok:
            return redirect(url_for("review_detail", rid=rid))
        values = dict(request.form)
    else:
        values = {"paper_id": request.args.get("paper_id", ""),
                  "review_submission_date": datetime.now().strftime("%Y-%m-%d")}
    with engine.connect() as conn:
        return render_template("review_form.html", r=values, action="Create", **review_choices(conn))


@app.route("/reviews/<int:rid>/edit", methods=["GET", "POST"])
def review_edit(rid):
    if request.method == "POST":
        def work(conn):
            d = load_review_form()
            check_no_self_review(conn, d["paper_id"], [d["reviewer_id"]])
            res = conn.execute(text("""
                UPDATE review SET paper_id = :paper_id, reviewer_id = :reviewer_id,
                    overall_score = :overall_score, recommendation = :recommendation,
                    comments_for_authors = :comments_for_authors,
                    confidential_comments = :confidential_comments,
                    review_submission_date = :review_submission_date
                WHERE review_id = :rid"""), {**d, "rid": rid})
            if res.rowcount == 0:
                raise ValidationError("review not found.")

        ok, _ = run_tx(work, "Review updated.")
        if ok:
            return redirect(url_for("review_detail", rid=rid))
        values = dict(request.form)
    else:
        with engine.connect() as conn:
            r = one(conn, "SELECT * FROM review WHERE review_id = :id", id=rid)
        if r is None:
            abort(404)
        values = {k: ("" if v is None else str(v)) for k, v in r.items()}
    with engine.connect() as conn:
        return render_template("review_form.html", r=values, action="Update", rid=rid,
                               **review_choices(conn))


@app.route("/reviews/<int:rid>/delete", methods=["POST"])
def review_delete(rid):
    def work(conn):
        if conn.execute(text("DELETE FROM review WHERE review_id = :id"), {"id": rid}).rowcount == 0:
            raise ValidationError("review not found.")

    ok, _ = run_tx(work, f"Review {rid} deleted.")
    return redirect(url_for("reviews") if ok else url_for("review_detail", rid=rid))


# ------------------------------------------------------------------ sessions
def session_choices(conn):
    return {
        "conferences": rows(conn, "SELECT conference_id, acronym, city FROM conference ORDER BY conference_id"),
        "reviewers": review_choices(conn)["reviewers"],
    }


def load_session_form():
    f = request.form
    d = {
        "conference_id": int(f["conference_id"]) if f.get("conference_id") else None,
        "title": f.get("title", "").strip(),
        "session_date": blank_to_none(f.get("session_date")),
        "start_time": blank_to_none(f.get("start_time")),
        "end_time": blank_to_none(f.get("end_time")),
        "room_label": f.get("room_label", "").strip(),
        "chair_id": int(f["chair_id"]) if f.get("chair_id") else None,
    }
    if any(v in (None, "") for v in d.values()):
        raise ValidationError("all session fields are required.")
    return d


@app.route("/sessions")
def sessions():
    with engine.connect() as conn:
        items = rows(conn, """
            SELECT s.*, c.acronym, c.city, u.given_name || ' ' || u.surname AS chair,
                   (SELECT COUNT(*) FROM paper p WHERE p.session_id = s.session_id) AS papers
            FROM conference_session s JOIN conference c ON c.conference_id = s.conference_id
            JOIN app_user u ON u.user_id = s.chair_id
            ORDER BY s.conference_id, s.session_date, s.start_time""")
    return render_template("sessions.html", items=items)


@app.route("/sessions/<int:sid>")
def session_detail(sid):
    with engine.connect() as conn:
        s = one(conn, """
            SELECT s.*, c.acronym, u.given_name || ' ' || u.surname AS chair
            FROM conference_session s JOIN conference c ON c.conference_id = s.conference_id
            JOIN app_user u ON u.user_id = s.chair_id WHERE s.session_id = :id""", id=sid)
        if s is None:
            abort(404)
        assigned = rows(conn, """
            SELECT p.paper_id, p.title, p.status, t.name AS track
            FROM paper p JOIN track t ON t.track_id = p.track_id
            WHERE p.session_id = :id ORDER BY p.paper_id""", id=sid)
        candidates = rows(conn, """
            SELECT p.paper_id, p.title, p.status, c.acronym, p.session_id
            FROM paper p JOIN track t ON t.track_id = p.track_id
            JOIN conference c ON c.conference_id = t.conference_id
            WHERE p.session_id IS DISTINCT FROM :id ORDER BY p.paper_id""", id=sid)
    return render_template("session_detail.html", s=s, assigned=assigned, candidates=candidates)


@app.route("/sessions/new", methods=["GET", "POST"])
def session_new():
    if request.method == "POST":
        def work(conn):
            d = load_session_form()
            return conn.execute(text("""
                INSERT INTO conference_session (conference_id, title, session_date, start_time,
                    end_time, room_label, chair_id)
                VALUES (:conference_id, :title, :session_date, :start_time, :end_time,
                    :room_label, :chair_id)
                RETURNING session_id"""), d).scalar_one()

        ok, sid = run_tx(work, "Session created.")
        if ok:
            return redirect(url_for("session_detail", sid=sid))
        values = dict(request.form)
    else:
        values = {}
    with engine.connect() as conn:
        return render_template("session_form.html", s=values, action="Create", **session_choices(conn))


@app.route("/sessions/<int:sid>/edit", methods=["GET", "POST"])
def session_edit(sid):
    if request.method == "POST":
        def work(conn):
            d = load_session_form()
            # Check 2: changing the session's conference must not orphan its assigned papers.
            for p in rows(conn, """
                    SELECT p.paper_id, p.status, p.track_id FROM paper p
                    WHERE p.session_id = :sid""", sid=sid):
                track_conf = conn.execute(text("SELECT conference_id FROM track WHERE track_id = :t"),
                                          {"t": p["track_id"]}).scalar_one()
                if track_conf != d["conference_id"]:
                    raise ValidationError(
                        f"invalid session assignment: assigned paper {p['paper_id']} belongs to "
                        f"conference {track_conf}; unassign it before moving the session.")
            res = conn.execute(text("""
                UPDATE conference_session SET conference_id = :conference_id, title = :title,
                    session_date = :session_date, start_time = :start_time, end_time = :end_time,
                    room_label = :room_label, chair_id = :chair_id
                WHERE session_id = :sid"""), {**d, "sid": sid})
            if res.rowcount == 0:
                raise ValidationError("session not found.")

        ok, _ = run_tx(work, "Session updated.")
        if ok:
            return redirect(url_for("session_detail", sid=sid))
        values = dict(request.form)
    else:
        with engine.connect() as conn:
            s = one(conn, "SELECT * FROM conference_session WHERE session_id = :id", id=sid)
        if s is None:
            abort(404)
        values = {k: ("" if v is None else str(v)) for k, v in s.items()}
        for key in ("start_time", "end_time"):
            values[key] = values[key][:5]
    with engine.connect() as conn:
        return render_template("session_form.html", s=values, action="Update", sid=sid,
                               **session_choices(conn))


@app.route("/sessions/<int:sid>/delete", methods=["POST"])
def session_delete(sid):
    def work(conn):
        res = conn.execute(text("DELETE FROM conference_session WHERE session_id = :id"), {"id": sid})
        if res.rowcount == 0:
            raise ValidationError("session not found.")

    ok, _ = run_tx(work, f"Session {sid} deleted; its papers are now unscheduled.")
    return redirect(url_for("sessions") if ok else url_for("session_detail", sid=sid))


@app.route("/sessions/<int:sid>/assign", methods=["POST"])
def session_assign(sid):
    pid = request.form.get("paper_id", type=int)

    def work(conn):
        p = one(conn, "SELECT status, track_id FROM paper WHERE paper_id = :id", id=pid)
        if p is None:
            raise ValidationError("paper not found.")
        check_session_assignment(conn, p["status"], p["track_id"], sid)
        conn.execute(text("UPDATE paper SET session_id = :s WHERE paper_id = :p"), {"s": sid, "p": pid})

    run_tx(work, f"Paper {pid} assigned to session {sid}.")
    return redirect(url_for("session_detail", sid=sid))


@app.route("/sessions/<int:sid>/unassign/<int:pid>", methods=["POST"])
def session_unassign(sid, pid):
    def work(conn):
        conn.execute(text("UPDATE paper SET session_id = NULL WHERE paper_id = :p AND session_id = :s"),
                     {"p": pid, "s": sid})

    run_tx(work, f"Paper {pid} removed from session {sid}.")
    return redirect(url_for("session_detail", sid=sid))


ensure_database()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
