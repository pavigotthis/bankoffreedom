import functools
import hashlib
import json
import os
import secrets
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import NoReturn

import click
from flask import Flask, abort, g, jsonify, redirect, render_template, request, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .domain import (
    DEFAULT_CONFIG,
    EVIDENCE_TYPES,
    IDS,
    INPUT_TYPES,
    LOCKED,
    PENDING,
    SHORT,
    STAGES,
    STRINGS,
    TEXT,
    config_validate,
    mapping_gaps,
    obj,
    step_schema,
    validate,
    validate_maps,
    validate_output,
)

ROOT = Path(__file__).resolve().parent.parent


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(s):
    return hashlib.sha256(s.encode()).hexdigest()


def packed(v):
    return json.dumps(v, separators=(",", ":"))


def create_app(test_config=None):
    app = Flask(
        __name__,
        template_folder=str(ROOT / "templates"),
        static_folder=str(ROOT / "static"),
        instance_path=str(ROOT / "instance"),
    )
    app.config.update(
        DATABASE=os.getenv("DATABASE_PATH", str(ROOT / "instance/3du.sqlite3")),
        SYNTHETIC_ONLY=os.getenv("SYNTHETIC_ONLY", "1") == "1",
        COOKIE_SECURE=os.getenv("COOKIE_SECURE", "0") == "1",
        MAX_CONTENT_LENGTH=1024 * 1024,
        MAPPING_PROVIDER=None,
        SESSION_SECONDS=8 * 3600,
        RECOVERY_DIR=os.getenv("RECOVERY_DIR", str(ROOT / "instance/recovery")),
    )
    if test_config:
        app.config.update(test_config)
    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)

    def db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"], timeout=15, isolation_level=None)
            os.chmod(app.config["DATABASE"], 0o600)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys=ON")
            g.db.execute("PRAGMA busy_timeout=15000")
        return g.db

    def rows(sql, args=()):
        return [dict(x) for x in db().execute(sql, args).fetchall()]

    def one(sql, args=()):
        r = db().execute(sql, args).fetchone()
        return dict(r) if r else None

    def audit(action, sid=None, rid=None, reason=""):
        db().execute(
            "INSERT INTO audit(actor_id,student_id,action,record_id,reason,created) VALUES(?,?,?,?,?,?)",
            (g.user["id"] if g.get("user") else None, sid, action, rid, reason, now()),
        )

    def cfg():
        r = one("SELECT * FROM settings WHERE id=1")
        return r["version"], json.loads(r["body"])

    def transaction(fn):
        @functools.wraps(fn)
        def wrapped(*a, **kw):
            db().execute("BEGIN IMMEDIATE")
            try:
                result = fn(*a, **kw)
                db().execute("COMMIT")
                return result
            except BaseException:
                db().execute("ROLLBACK")
                raise

        return wrapped

    def error(msg: str, status: int = 400) -> NoReturn:
        abort(status, description=msg)

    def data():
        if request.is_json:
            v = request.get_json()
        elif "payload" in request.form:
            try:
                v = json.loads(request.form["payload"])
            except ValueError:
                error("Enter valid JSON; nothing was saved.")
        else:
            v = request.form.to_dict()
        if not isinstance(v, dict):
            error("An object is required.")
        return v

    def reason(d):
        s = d.get("reason", "")
        if not isinstance(s, str) or not s.strip() or len(s) > 2000:
            error("A review or change reason is required.")
        return s.strip()

    def need_role(*roles):
        if not g.user:
            error("Please sign in.", 401)
        if g.user["role"] not in roles:
            error("You do not have permission for this action.", 403)

    def relation(sid, kind):
        return one(
            "SELECT * FROM relationships WHERE actor_id=? AND student_id=? AND kind=?",
            (g.user["id"], sid, kind),
        )

    def access(sid, *roles):
        need_role(*roles)
        role = g.user["role"]
        if role == "student" and g.user["id"] != sid:
            error("You do not have access to this student.", 403)
        if role != "student" and not relation(sid, role):
            error("No authorized relationship with this student.", 403)
        if not one("SELECT id FROM users WHERE id=? AND role='student'", (sid,)):
            error("Student not found.", 404)

    def stage(sid, n):
        return one("SELECT * FROM stages WHERE student_id=? AND stage=?", (sid, n))

    def next_stage(sid):
        for n in range(1, 9):
            if stage(sid, n)["status"] != "complete":
                return n
        return 9

    def unlocked(sid, n):
        return n in (1, 9) or all(stage(sid, k)["status"] == "complete" for k in range(1, n))

    def progress(sid):
        return {
            "stages": [
                {
                    "number": n,
                    "name": name,
                    "status": stage(sid, n)["status"] if n < 9 else "available",
                    "available": unlocked(sid, n),
                }
                for n, name in enumerate(STAGES, 1)
            ],
            "next_stage": next_stage(sid),
        }

    def public_report(sid):
        r = one(
            "SELECT r.id,r.version,r.maps,p.created AS published_at FROM publications p JOIN reports r ON r.id=p.report_id WHERE p.student_id=? ORDER BY p.id DESC LIMIT 1",
            (sid,),
        )
        if not r:
            return {"status": "pending", "message": PENDING}
        maps = json.loads(r["maps"])
        if cfg()[1].get("mapping_profile", {}).get("kind") == "3du-standalone":
            for role in ["student", "parent"]:
                # Historic publications stay intact; never expose their full analytical arrays.
                maps[role + "_journey"] = {
                    "summary": maps[role + "_journey"]["summary"],
                    "items": [],
                }
        return {
            "status": "published",
            "version": r["version"],
            "published_at": r["published_at"],
            "maps": maps,
        }

    def invalidate(sid, why, run_id=None, from_step=1):
        rs = rows(
            "SELECT id FROM runs WHERE student_id=?" + (" AND id=?" if run_id else ""),
            (sid, run_id) if run_id else (sid,),
        )
        for r in rs:
            db().execute("UPDATE runs SET status='stale' WHERE id=?", (r["id"],))
            db().execute(
                "UPDATE steps SET status='stale' WHERE run_id=? AND step>=? AND status='valid'",
                (r["id"], from_step),
            )
            db().execute(
                "UPDATE reports SET status='stale' WHERE run_id=? AND status='draft'", (r["id"],)
            )
        audit("dependency-invalidation", sid, run_id, why)

    def mentor_scope(sid):
        scope = json.loads(relation(sid, "mentor")["scopes"])
        return scope if isinstance(scope, dict) else {"stages": scope, "fields": {}}

    def mentor_work(sid, n):
        s = stage(sid, n)
        draft = json.loads(s["draft"])
        fields = mentor_scope(sid)["fields"].get(str(n), [])
        return {
            "stage": n,
            "status": s["status"],
            "revision": s["revision"],
            "draft": {k: v for k, v in draft.items() if k in fields},
        }

    def readiness(sid, c):
        mandatory_gaps = []
        if c.get("mapping_profile", {}).get("kind") == "3du-standalone":
            from .standalone import MANDATORY

            for role in ["student", "parent"]:
                entries = rows(
                    "SELECT actor_id,submitted FROM intake_entries WHERE student_id=? AND role=? AND submitted IS NOT NULL",
                    (sid, role),
                )
                valid = any(
                    (
                        role == "student"
                        or one(
                            "SELECT actor_id FROM relationships WHERE actor_id=? AND student_id=? AND kind='parent'",
                            (e["actor_id"], sid),
                        )
                    )
                    and all(
                        json.loads(e["submitted"]).get(label, "").strip()
                        for label in MANDATORY[role]
                    )
                    for e in entries
                )
                if not valid:
                    mandatory_gaps.append("Mandatory " + role + " input submission")
            mandatory_gaps.append(
                "Professional-note applicability and educator authorization require owner setup."
            )
        if not c["readiness"]:
            return mandatory_gaps + ["Mapping readiness criteria have not been approved."]
        missing = [
            f"Stage {n} completion"
            for n in c["readiness"]["required_stages"]
            if stage(sid, n)["status"] != "complete"
        ]
        snap = one(
            "SELECT id FROM snapshots WHERE student_id=? ORDER BY version DESC LIMIT 1", (sid,)
        )
        version, _ = cfg()
        for kind in ["assessments", "mentor_interview", "activities"]:
            if not snap or not one(
                "SELECT actor_id FROM readiness_reviews WHERE snapshot_id=? AND kind=? AND config_version=?",
                (snap["id"], kind, version),
            ):
                missing.append("Source-backed readiness review: " + kind)
        return mandatory_gaps + missing

    def input_bundle(sid):
        inputs = rows(
            "SELECT e.* FROM evidence e WHERE e.student_id=? AND NOT EXISTS(SELECT 1 FROM evidence newer WHERE newer.corrected_from=e.id) ORDER BY e.id",
            (sid,),
        )
        work = rows(
            "SELECT stage,draft,status,revision FROM stages WHERE student_id=? ORDER BY stage",
            (sid,),
        )
        return {"evidence": inputs, "student_work": work}

    def snapshot_current(run):
        snap = one("SELECT inputs FROM snapshots WHERE id=?", (run["snapshot_id"],))
        return snap and json.loads(snap["inputs"]) == input_bundle(run["student_id"])

    def current_run(run):
        v, c = cfg()
        latest = one(
            "SELECT id FROM snapshots WHERE student_id=? ORDER BY version DESC LIMIT 1",
            (run["student_id"],),
        )
        if (
            not snapshot_current(run)
            or run["config_version"] != v
            or not latest
            or run["snapshot_id"] != latest["id"]
            or run["status"] in ("stale", "failed", "blocked")
        ):
            error("The workflow is incomplete, failed, blocked or requires review.", 409)
        if readiness(run["student_id"], c):
            error("Required work is not complete.", 409)
        return c

    def run_record(rid):
        r = one("SELECT * FROM runs WHERE id=?", (rid,))
        if not r:
            error("Workflow not found.", 404)
        return r

    def report_record(rid):
        r = one("SELECT * FROM reports WHERE id=?", (rid,))
        if not r:
            error("Report not found.", 404)
        return r

    def valid_report(r):
        if r["status"] != "draft":
            error("This version is not an eligible current draft.", 409)
        run = run_record(r["run_id"])
        c = current_run(run)
        if run["status"] != "complete":
            error("All four workflow steps must be valid.", 409)
        validate_maps(c, json.loads(r["maps"]))
        return c

    def response(value, sid=None):
        return (
            jsonify(value)
            if request.is_json or request.path.startswith("/api/")
            else redirect(url_for("workspace", sid=sid) if sid else url_for("portal"))
        )

    @app.teardown_appcontext
    def close(exc):
        if "db" in g:
            g.db.close()

    @app.before_request
    def authenticate():
        g.user = None
        g.session = None
        g.new_session = None
        t = request.cookies.get("three_du_session", "")
        s = (
            one("SELECT * FROM sessions WHERE token=? AND expires>?", (digest(t), int(time.time())))
            if t
            else None
        )
        if not s:
            t = secrets.token_urlsafe(32)
            s = {
                "token": digest(t),
                "user_id": None,
                "csrf": secrets.token_urlsafe(32),
                "expires": int(time.time()) + app.config["SESSION_SECONDS"],
            }
            db().execute("INSERT INTO sessions VALUES(:token,:user_id,:csrf,:expires)", s)
            g.new_session = t
        g.session = s
        if s["user_id"]:
            g.user = one(
                "SELECT id,email,name,role,synthetic FROM users WHERE id=?", (s["user_id"],)
            )
        # Guard the whole admin namespace before record lookup or CSRF handling.
        if (
            request.path == "/portal/admin"
            or request.path.startswith("/api/admin/")
            or (request.path.startswith("/admin/") and request.path != "/admin/login")
        ):
            if not g.user:
                if request.path.startswith("/api/") or request.is_json:
                    error("Please sign in as an administrator.", 401)
                return redirect(
                    "/admin/login"
                    + ("?expired=1" if request.cookies.get("three_du_session") else "")
                )
            need_role("admin")
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            if not app.config["SYNTHETIC_ONLY"] and request.path not in (
                "/login",
                "/admin/login",
                "/logout",
                "/recover",
                "/reset",
            ):
                error(
                    "Live data collection is blocked pending approved policies and a separate release review.",
                    409,
                )
            token = request.headers.get("X-CSRF-Token") or request.form.get("csrf", "")
            if not secrets.compare_digest(token, s["csrf"]):
                error("The form expired. Refresh the page and try again.", 403)

    @app.after_request
    def headers(resp):
        if g.get("new_session"):
            resp.set_cookie(
                "three_du_session",
                g.new_session,
                max_age=app.config["SESSION_SECONDS"],
                httponly=True,
                secure=app.config["COOKIE_SECURE"],
                samesite="Lax",
            )
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "same-origin"
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'self'"
        )
        return resp

    app.jinja_env.filters["fromjson"] = json.loads
    app.jinja_env.filters["prettyjson"] = lambda value: json.dumps(
        json.loads(value), indent=2, ensure_ascii=False
    )

    @app.context_processor
    def globals_():
        return {
            "user": g.user,
            "csrf": g.session["csrf"],
            "stages": STAGES,
            "pending": PENDING,
            "synthetic_only": app.config["SYNTHETIC_ONLY"],
            "status_labels": {
                "empty": "Not started",
                "draft": "Draft saved",
                "submitted": "Submitted for review",
                "complete": "Completed",
                "available": "Available",
            },
            "has_mapping_setup": bool(
                g.user
                and g.user["role"] == "admin"
                and one(
                    "SELECT actor_id FROM admin_capabilities WHERE actor_id=? AND capability='mapping_setup'",
                    (g.user["id"],),
                )
            ),
        }

    @app.errorhandler(400)
    @app.errorhandler(401)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(409)
    @app.errorhandler(413)
    @app.errorhandler(429)
    def failure(e):
        if request.path.startswith("/api/") or request.is_json:
            return jsonify(error=e.description), e.code
        modes = {
            "/signup": "signup",
            "/login": "login",
            "/admin/login": "login",
            "/recover": "recover",
            "/reset": "reset",
        }
        if request.method == "POST" and request.path in modes:
            safe_values = {
                key: request.form.get(key, "")[:limit]
                for key, limit in [("email", 254), ("name", 120), ("role", 20), ("synthetic", 3)]
            }
            return render_template(
                "auth.html",
                mode=modes[request.path],
                admin_login=request.path == "/admin/login",
                form_values=safe_values,
                form_error=e.description,
                reset_token=request.form.get("token", ""),
            ), e.code
        if request.method == "POST" and request.path == "/account/name" and g.user:
            return render_template(
                "account_name.html",
                form_error=e.description,
                entered_name=request.form.get("name", "")[:120],
            ), e.code
        return render_template("error.html", message=e.description, status=e.code), e.code

    @app.errorhandler(ValueError)
    def invalid(e):
        return failure(type("ValidationError", (), {"description": str(e), "code": 400})())

    def rate(key, limit=10):
        key = digest(key + request.remote_addr)
        t = int(time.time())
        r = one("SELECT * FROM rate_limits WHERE key=?", (key,))
        if not r or t - r["window"] > 900:
            db().execute("INSERT OR REPLACE INTO rate_limits VALUES(?,?,?)", (key, 1, t))
        elif r["attempts"] >= limit:
            error("Too many attempts. Try again in fifteen minutes.", 429)
        else:
            db().execute("UPDATE rate_limits SET attempts=attempts+1 WHERE key=?", (key,))

    def rotate(uid):
        db().execute("DELETE FROM sessions WHERE token=?", (g.session["token"],))
        t = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(32)
        db().execute(
            "INSERT INTO sessions VALUES(?,?,?,?)",
            (digest(t), uid, csrf, int(time.time()) + app.config["SESSION_SECONDS"]),
        )
        g.new_session = t

    def email_and_password(d):
        if not isinstance(d.get("email", ""), str) or not isinstance(d.get("password", ""), str):
            error("Email and password must be text.")
        email = d.get("email", "").strip().lower()
        pw = d.get("password", "")
        if len(email) > 254 or "@" not in email or "." not in email.split("@")[-1]:
            error("Enter a valid email address.")
        if not isinstance(pw, str) or len(pw) < 12 or len(pw) > 256:
            error("Use a password with 12–256 characters.")
        return email, pw

    @app.get("/")
    def home():
        return render_template("home.html")

    @app.get("/health")
    def health():
        db().execute("SELECT 1")
        return jsonify(status="ok", mode="synthetic-development-only")

    @app.get("/api/session")
    def session_info():
        return jsonify(csrf=g.session["csrf"], user=g.user)

    def account_name(value):
        if not isinstance(value, str) or not value.strip() or len(value.strip()) > 120:
            error("Enter your name (1–120 characters).")
        if any(ord(character) < 32 or ord(character) == 127 for character in value):
            error("Enter your name without control characters.")
        return value.strip()

    @app.route("/account/name", methods=["GET", "POST"])
    @transaction
    def edit_account_name():
        need_role("student", "parent")
        if request.method == "GET":
            return render_template("account_name.html")
        name = account_name(data().get("name"))
        db().execute("UPDATE users SET name=? WHERE id=?", (name, g.user["id"]))
        audit(
            "account-name-update",
            g.user["id"] if g.user["role"] == "student" else None,
            g.user["id"],
            "Account owner updated display name; no relationship or role changed",
        )
        return (
            jsonify(name=name)
            if request.is_json
            else redirect(url_for("edit_account_name", saved=1))
        )

    @app.route("/signup", methods=["GET", "POST"])
    @transaction
    def signup():
        if request.method == "GET":
            return render_template("auth.html", mode="signup")
        rate("signup")
        if not app.config["SYNTHETIC_ONLY"]:
            error("Live registration is blocked pending approved minor-data policies.", 409)
        d = data()
        email, pw = email_and_password(d)
        if d.get("role") not in ("student", "parent"):
            error("Only student and parent accounts can self-register.", 403)
        if d.get("synthetic") not in (True, "yes"):
            error("Use fictional development data only and confirm the notice.")
        name = account_name(d.get("name"))
        try:
            uid = (
                db()
                .execute(
                    "INSERT INTO users(email,password,role,name) VALUES(?,?,?,?)",
                    (email, generate_password_hash(pw), d["role"], name),
                )
                .lastrowid
            )
        except sqlite3.IntegrityError:
            error("Registration could not be completed. Try signing in or account recovery.", 409)
        if d["role"] == "student":
            db().executemany(
                "INSERT INTO stages(student_id,stage) VALUES(?,?)", [(uid, n) for n in range(1, 9)]
            )
        rotate(uid)
        audit("signup", uid if d["role"] == "student" else None)
        return response({"role": d["role"], "redirect": "/portal"})

    @app.route("/admin/login", methods=["GET", "POST"])
    @app.route("/login", methods=["GET", "POST"])
    def login():
        admin_login = request.path == "/admin/login"
        if request.method == "GET":
            if admin_login and g.user:
                need_role("admin")
                return redirect("/admin/dashboard")
            return render_template(
                "auth.html",
                mode="login",
                admin_login=admin_login,
                expired=request.args.get("expired") == "1",
            )
        d = data()
        if not isinstance(d.get("email", ""), str) or not isinstance(d.get("password", ""), str):
            error("Email and password must be text.")
        email = d.get("email", "").strip().lower()
        rate("login:" + email)
        u = one("SELECT * FROM users WHERE email=?", (email,))
        # Perform a password hash even for nonexistent accounts.
        hashed = u["password"] if u else generate_password_hash("unused-development-password")
        if not check_password_hash(hashed, d.get("password", "")) or not u:
            error("Email or password is incorrect.", 401)
        if admin_login and u["role"] != "admin":
            error("This account does not have administrator access.", 403)
        rotate(u["id"])
        destination = "/admin/dashboard" if u["role"] == "admin" else "/portal"
        return (
            jsonify(role=u["role"], redirect=destination)
            if request.is_json
            else redirect(destination)
        )

    @app.post("/logout")
    def logout():
        rotate(None)
        return jsonify(status="signed out") if request.is_json else redirect("/")

    @app.route("/recover", methods=["GET", "POST"])
    def recover():
        if request.method == "GET":
            return render_template("auth.html", mode="recover")
        d = data()
        if not isinstance(d.get("email", ""), str) or not isinstance(d.get("password", ""), str):
            error("Email and password must be text.")
        email = d.get("email", "").strip().lower()
        rate("recover:" + email, 5)
        u = one("SELECT * FROM users WHERE email=?", (email,))
        if u:
            token = secrets.token_urlsafe(32)
            db().execute(
                "INSERT INTO recovery VALUES(?,?,?,0)",
                (digest(token), u["id"], int(time.time()) + 1800),
            )
            # Local-only delivery adapter. No public response exposes a token.
            dest = Path(app.config["RECOVERY_DIR"])
            dest.mkdir(parents=True, exist_ok=True, mode=0o700)
            path = dest / (secrets.token_hex(12) + ".json")
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as f:
                json.dump({"email": email, "path": "/reset?token=" + token, "synthetic": True}, f)
        return (
            jsonify(message="If an account exists, recovery instructions have been prepared.")
            if request.is_json
            else render_template(
                "notice.html",
                title="Check your recovery instructions",
                message="If an account exists, recovery instructions have been prepared. Local development delivery is available to the authorized operator; email delivery is not connected.",
            )
        )

    @app.route("/reset", methods=["GET", "POST"])
    def reset():
        if request.method == "GET":
            return render_template(
                "auth.html", mode="reset", reset_token=request.args.get("token", "")
            )
        d = data()
        rate("reset", 10)
        pw = d.get("password", "")
        if not isinstance(pw, str):
            error("Password must be text.")
        if len(pw) < 12 or len(pw) > 256:
            error("Use a password with 12–256 characters.")
        db().execute("BEGIN IMMEDIATE")
        try:
            r = one(
                "SELECT * FROM recovery WHERE token=? AND used=0 AND expires>?",
                (digest(d.get("token", "")), int(time.time())),
            )
            if not r:
                error("This recovery link is invalid or expired.", 400)
            db().execute(
                "UPDATE users SET password=? WHERE id=?", (generate_password_hash(pw), r["user_id"])
            )
            db().execute("UPDATE recovery SET used=1 WHERE user_id=?", (r["user_id"],))
            db().execute("DELETE FROM sessions WHERE user_id=?", (r["user_id"],))
            db().execute("COMMIT")
        except BaseException:
            db().execute("ROLLBACK")
            raise
        rotate(None)
        return jsonify(status="password reset") if request.is_json else redirect("/login")

    @app.get("/portal")
    def portal():
        if not g.user:
            return redirect("/login")
        role = g.user["role"]
        if role == "student":
            return redirect(url_for("student_stage", n=next_stage(g.user["id"])))
        if role == "admin":
            return redirect("/admin/dashboard")
        linked = rows(
            "SELECT u.id,u.email,u.name FROM relationships r JOIN users u ON u.id=r.student_id WHERE r.actor_id=? AND r.kind=?",
            (g.user["id"], role),
        )
        return render_template("portal.html", role=role, students=linked)

    @app.get("/portal/<role>")
    def role_portal(role):
        need_role(role) if role in ["student", "parent", "mentor", "admin"] else error(
            "Portal not found.", 404
        )
        return portal()

    @app.get("/student/stages/<int:n>")
    def student_stage(n):
        need_role("student")
        sid = g.user["id"]
        if not 1 <= n <= 9:
            error("Stage not found.", 404)
        p = progress(sid)
        if not unlocked(sid, n):
            return render_template("locked.html", progress=p, message=LOCKED), 403
        if n == 9:
            return render_template("shared.html", progress=p, report=public_report(sid), sid=sid)
        intake_context = intake_view(sid) if n == 1 else {}
        return render_template(
            "stage.html",
            **intake_context,
            n=n,
            stage=stage(sid, n),
            progress=p,
            rule=cfg()[1]["stage_rules"].get(str(n)),
            intake_enabled=bool(cfg()[1].get("mapping_profile")),
            report=public_report(sid) if n == 8 else None,
        )

    @app.get("/api/students/<int:sid>/progress")
    def get_progress(sid):
        access(sid, "student", "parent")
        return jsonify(progress(sid))

    @app.get("/api/students/<int:sid>/report")
    def get_report(sid):
        access(sid, "student", "parent")
        return jsonify(public_report(sid))

    @app.get("/parent/students/<int:sid>")
    def parent_student(sid):
        access(sid, "parent")
        return render_template(
            "shared.html", sid=sid, progress=progress(sid), report=public_report(sid)
        )

    @app.route("/api/students/<int:sid>/stages/<int:n>", methods=["GET", "POST"])
    def work(sid, n):
        access(sid, "student")
        if not 1 <= n <= 8:
            error("Stage not found.", 404)
        if not unlocked(sid, n):
            return jsonify(error=LOCKED, next_action=f"/student/stages/{next_stage(sid)}"), 403
        s = stage(sid, n)
        if request.method == "GET":
            return jsonify(
                stage=n, status=s["status"], revision=s["revision"], draft=json.loads(s["draft"])
            )
        if n == 1 and (
            cfg()[1].get("mapping_profile")
            or one(
                "SELECT id FROM intake_entries WHERE student_id=? AND actor_id=?",
                (sid, g.user["id"]),
            )
        ):
            error(
                "Use the profile input form; this endpoint cannot bypass its resubmission limit.",
                409,
            )
        return save_work(sid, n, s)

    @transaction
    def save_work(sid, n, s):
        d = data()
        validate(
            obj(
                {
                    "action": {"enum": ["save", "submit"]},
                    "revision": {"type": "integer"},
                    "draft": {"type": "object", "additionalProperties": TEXT, "maxProperties": 30},
                }
            ),
            d,
        )
        s = stage(sid, n)
        if s["status"] == "complete":
            error("Completed work is view-only. Request a reviewed correction from the team.", 409)
        if s["revision"] != d["revision"]:
            error("Work changed in another session. Reload before saving.", 409)
        status = "submitted" if d["action"] == "submit" else "draft"
        db().execute(
            "UPDATE stages SET draft=?,status=?,revision=revision+1 WHERE student_id=? AND stage=?",
            (packed(d["draft"]), status, sid, n),
        )
        invalidate(sid, "Student work changed; downstream mappings require review.")
        audit("stage-" + d["action"], sid, n)
        return jsonify(status=status, revision=s["revision"] + 1, completed=False)

    @app.post("/api/students/<int:sid>/stages/<int:n>/approve")
    @transaction
    def approve_stage(sid, n):
        access(sid, "admin", "mentor")
        if not 1 <= n <= 8:
            error("Stage not found.", 404)
        d = data()
        why = reason(d)
        v, c = cfg()
        rule = c["stage_rules"].get(str(n))
        if not rule:
            error("Stage completion criteria and approval authority are not configured.", 409)
        if g.user["role"] not in rule["approvers"]:
            error("This role cannot approve this stage.", 403)
        if g.user["role"] == "mentor" and n not in mentor_scope(sid)["stages"]:
            error("This stage is outside the approved mentor scope.", 403)
        if g.user["role"] == "mentor" and not set(rule["required_draft_fields"]) <= set(
            mentor_scope(sid)["fields"].get(str(n), [])
        ):
            error("Required evidence fields are outside your approved review scope.", 403)
        s = stage(sid, n)
        if str(d.get("revision")) != str(s["revision"]):
            error("Review the exact current work revision.", 409)
        if rule["requires_submission"] and s["status"] not in ("submitted", "complete"):
            error("Submission is required by the approved criteria.", 409)
        if any(not json.loads(s["draft"]).get(k) for k in rule["required_draft_fields"]):
            error("Required evidence is missing.", 409)
        if s["status"] != "complete":
            db().execute(
                "UPDATE stages SET status='complete',revision=revision+1 WHERE student_id=? AND stage=?",
                (sid, n),
            )
            invalidate(sid, "Stage completion changed snapshot work; review downstream mappings.")
            audit("stage-completion-approval", sid, n, why)
        return response({"status": "complete"}, sid)

    def student_relationships(sid):
        return rows(
            "SELECT u.email,u.name,r.kind,r.scopes FROM relationships r JOIN users u ON u.id=r.actor_id WHERE r.student_id=? AND r.kind IN ('parent','mentor') ORDER BY r.kind,u.email",
            (sid,),
        )

    @app.get("/admin/dashboard")
    def admin_dashboard():
        need_role("admin")
        students = rows(
            "SELECT u.id,u.email,u.name FROM relationships r JOIN users u ON u.id=r.student_id WHERE r.actor_id=? AND r.kind='admin' ORDER BY u.email",
            (g.user["id"],),
        )
        for student in students:
            sid = student["id"]
            student["progress"] = progress(sid)
            student["relationships"] = student_relationships(sid)
        audit("admin-dashboard-inspection")
        return render_template("admin_dashboard.html", students=students)

    @app.get("/api/admin/students/<int:sid>/relationships")
    def admin_relationships(sid):
        access(sid, "admin")
        audit("admin-relationship-inspection", sid)
        return jsonify(relationships=student_relationships(sid))

    @app.get("/admin/students/<int:sid>")
    def workspace(sid):
        access(sid, "admin")
        audit("admin-record-inspection", sid)
        v, c = cfg()
        runs = rows("SELECT * FROM runs WHERE student_id=? ORDER BY id DESC", (sid,))
        for r in runs:
            r["steps"] = rows(
                "SELECT * FROM steps WHERE run_id=? ORDER BY step,attempt", (r["id"],)
            )
        reports = rows("SELECT * FROM reports WHERE student_id=? ORDER BY version DESC", (sid,))
        for r in reports:
            r["approvals"] = rows(
                "SELECT actor_id,role,reason,created FROM approvals WHERE report_id=?", (r["id"],)
            )
        return render_template(
            "admin.html",
            sid=sid,
            relationships=student_relationships(sid),
            progress=progress(sid),
            work=rows("SELECT * FROM stages WHERE student_id=?", (sid,)),
            evidence=rows("SELECT * FROM evidence WHERE student_id=? ORDER BY id", (sid,)),
            snapshots=rows(
                "SELECT * FROM snapshots WHERE student_id=? ORDER BY version DESC", (sid,)
            ),
            runs=runs,
            reports=reports,
            history=rows("SELECT * FROM audit WHERE student_id=? ORDER BY id DESC", (sid,)),
            notes=rows("SELECT * FROM notes WHERE student_id=?", (sid,)),
            config=c,
            config_version=v,
            gaps=mapping_gaps(c) + readiness(sid, c),
            mapping_spec=private_mapping_spec(c),
            intakes=rows(
                "SELECT e.id,e.actor_id,e.role,e.submitted,e.submitted_version,e.submissions,e.updated,u.email AS actor_email,u.name AS actor_name,(SELECT MIN(created) FROM intake_versions WHERE entry_id=e.id) AS first_submitted FROM intake_entries e JOIN users u ON u.id=e.actor_id WHERE e.student_id=? AND e.submitted IS NOT NULL",
                (sid,),
            ),
        )

    @app.get("/api/admin/students/<int:sid>")
    def admin_data(sid):
        access(sid, "admin")
        audit("admin-record-inspection", sid)
        return jsonify(
            evidence=rows("SELECT * FROM evidence WHERE student_id=?", (sid,)),
            snapshots=rows("SELECT * FROM snapshots WHERE student_id=?", (sid,)),
            runs=rows("SELECT * FROM runs WHERE student_id=?", (sid,)),
            reports=rows("SELECT * FROM reports WHERE student_id=?", (sid,)),
        )

    @app.get("/api/admin/config")
    def get_config():
        need_role("admin")
        v, c = cfg()
        return jsonify(version=v, configuration=c, missing=mapping_gaps(c))

    @app.get("/api/admin/schemas/steps/<int:n>")
    def get_step_schema(n):
        need_role("admin")
        if not 1 <= n <= 4:
            error("Step not found.", 404)
        version, c = cfg()
        return jsonify(
            config_version=version, schema=step_schema(n, c), blocked_by=mapping_gaps(c, n)
        )

    @app.post("/api/admin/config")
    @transaction
    def update_config():
        need_role("admin")
        d = data()
        why = reason(d)
        v, c = cfg()
        if d.get("version") != v:
            error("Configuration changed. Reload before saving.", 409)
        proposed = config_validate(d.get("configuration"))
        if (
            c.get("mapping_profile", {}).get("kind") == "3du-standalone"
            or proposed.get("mapping_profile", {}).get("kind") == "3du-standalone"
        ):
            setup_access()
            for key in [
                "mapping_profile",
                "mapping_details",
                "student_personas",
                "parent_personas",
                "empathy_categories",
                "journey_stages",
                "journey_fields",
            ]:
                if c.get(key) != proposed.get(key):
                    error("Use the versioned standalone setup review and activation process.", 409)
        c = proposed
        db().execute("UPDATE settings SET version=version+1,body=? WHERE id=1", (packed(c),))
        # Global specification changes invalidate every unpublished dependent artifact.
        for s in rows("SELECT id FROM users WHERE role='student'"):
            invalidate(s["id"], "Approved configuration changed: " + why)
        audit("configuration-change", None, v + 1, why)
        return response({"version": v + 1})

    @app.post("/api/admin/students/<int:sid>/evidence")
    @transaction
    def add_evidence(sid):
        access(sid, "admin")
        d = data()
        why = reason(d)
        validate(
            obj(
                {
                    "stakeholder": {"enum": ["student", "parent", "educator", "mentor"]},
                    "source": SHORT,
                    "type": {"enum": INPUT_TYPES + EVIDENCE_TYPES},
                    "statement": SHORT,
                    "reason": SHORT,
                    "corrected_from": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
                },
                ["stakeholder", "source", "type", "statement", "reason"],
            ),
            d,
        )
        prev = d.get("corrected_from")
        revision = 1
        if prev:
            old = one("SELECT * FROM evidence WHERE id=? AND student_id=?", (prev, sid))
            if not old:
                error("Source evidence not found.", 404)
            if one("SELECT id FROM evidence WHERE corrected_from=?", (prev,)):
                error("This evidence was already corrected. Review the latest version.", 409)
            revision = old["revision"] + 1
        eid = (
            db()
            .execute(
                "INSERT INTO evidence(student_id,stakeholder,source,type,statement,revision,corrected_from) VALUES(?,?,?,?,?,?,?)",
                (sid, d["stakeholder"], d["source"], d["type"], d["statement"], revision, prev),
            )
            .lastrowid
        )
        invalidate(sid, "Source evidence changed: " + why)
        audit("evidence-correction" if prev else "evidence-addition", sid, eid, why)
        return response({"id": eid, "revision": revision}, sid)

    @app.post("/api/admin/students/<int:sid>/snapshot")
    @transaction
    def snapshot(sid):
        access(sid, "admin")
        d = data()
        why = reason(d)
        inputs = rows(
            "SELECT e.* FROM evidence e WHERE e.student_id=? AND NOT EXISTS(SELECT 1 FROM evidence newer WHERE newer.corrected_from=e.id) ORDER BY e.id",
            (sid,),
        )
        # Work is included verbatim with attribution, never interpreted as an assessment.
        work = rows(
            "SELECT stage,draft,status,revision FROM stages WHERE student_id=? ORDER BY stage",
            (sid,),
        )
        version = one(
            "SELECT COALESCE(MAX(version),0)+1 AS v FROM snapshots WHERE student_id=?", (sid,)
        )["v"]
        nid = (
            db()
            .execute(
                "INSERT INTO snapshots(student_id,version,inputs,created) VALUES(?,?,?,?)",
                (sid, version, packed({"evidence": inputs, "student_work": work}), now()),
            )
            .lastrowid
        )
        invalidate(sid, "New input snapshot: " + why)
        audit("snapshot-created", sid, nid, why)
        return response({"id": nid, "version": version}, sid)

    @app.post("/api/admin/snapshots/<int:snap_id>/readiness")
    @transaction
    def readiness_review(snap_id):
        snap = one("SELECT * FROM snapshots WHERE id=?", (snap_id,))
        if not snap:
            error("Snapshot not found.", 404)
        sid = snap["student_id"]
        access(sid, "admin")
        d = data()
        why = reason(d)
        v, c = cfg()
        validate(
            obj(
                {
                    "kind": {"enum": ["assessments", "mentor_interview", "activities"]},
                    "evidence_ids": dict(IDS, minItems=1),
                    "reason": SHORT,
                }
            ),
            d,
        )
        if not c["readiness"]:
            error("Approved readiness criteria are required before a review.", 409)
        latest = one(
            "SELECT id FROM snapshots WHERE student_id=? ORDER BY version DESC LIMIT 1", (sid,)
        )
        if latest["id"] != snap_id or json.loads(snap["inputs"]) != input_bundle(sid):
            error("Review the latest current snapshot.", 409)
        evidence = {e["id"]: e for e in json.loads(snap["inputs"])["evidence"]}
        if any(i not in evidence for i in d["evidence_ids"]):
            error("Readiness review requires evidence from this snapshot.")
        if any(
            evidence[i]["type"] in ("assumption", "missing evidence") for i in d["evidence_ids"]
        ):
            error("Assumptions or missing evidence cannot prove completion.")
        db().execute(
            "INSERT OR IGNORE INTO readiness_reviews VALUES(?,?,?,?,?,?,?)",
            (snap_id, d["kind"], v, g.user["id"], packed(d["evidence_ids"]), why, now()),
        )
        audit("readiness-" + d["kind"], sid, snap_id, why)
        return response({"status": "reviewed", "kind": d["kind"]}, sid)

    @app.post("/api/admin/students/<int:sid>/runs")
    @transaction
    def start_run(sid):
        access(sid, "admin")
        d = data()
        why = reason(d)
        v, c = cfg()
        snap = one(
            "SELECT * FROM snapshots WHERE student_id=? ORDER BY version DESC LIMIT 1", (sid,)
        )
        if not snap:
            error("Save a versioned input snapshot first.", 409)
        gaps = (mapping_gaps(c, 1) if c.get("mapping_profile") else mapping_gaps(c)) + readiness(
            sid, c
        )
        status = "blocked" if gaps else "pending"
        rid = (
            db()
            .execute(
                "INSERT INTO runs(student_id,snapshot_id,config_version,status,created,specification_sha256) VALUES(?,?,?,?,?,?)",
                (
                    sid,
                    snap["id"],
                    v,
                    status,
                    now(),
                    c.get("mapping_profile", {}).get("source_sha256"),
                ),
            )
            .lastrowid
        )
        if gaps:
            db().execute(
                "INSERT INTO steps(run_id,step,attempt,status,input,summary,error,created) VALUES(?,1,1,?,?,?,?,?)",
                (
                    rid,
                    "blocked",
                    snap["inputs"],
                    "Generation not attempted",
                    "; ".join(gaps),
                    now(),
                ),
            )
        audit("workflow-created", sid, rid, why)
        return response({"id": rid, "status": status, "gaps": gaps}, sid)

    @app.get("/api/admin/runs/<int:rid>")
    def inspect_run(rid):
        r = run_record(rid)
        access(r["student_id"], "admin")
        audit("workflow-inspection", r["student_id"], rid)
        return jsonify(
            run=r,
            specification=imported_spec_by_hash(r.get("specification_sha256")),
            snapshot=one("SELECT * FROM snapshots WHERE id=?", (r["snapshot_id"],)),
            steps=rows("SELECT * FROM steps WHERE run_id=? ORDER BY step,attempt", (rid,)),
            readiness_reviews=rows(
                "SELECT * FROM readiness_reviews WHERE snapshot_id=?", (r["snapshot_id"],)
            ),
        )

    def latest_step(rid, n):
        return one(
            "SELECT * FROM steps WHERE run_id=? AND step=? ORDER BY attempt DESC LIMIT 1", (rid, n)
        )

    @app.post("/api/admin/runs/<int:rid>/steps/<int:n>")
    @transaction
    def record_step(rid, n, provider_generation=False):
        r = run_record(rid)
        sid = r["student_id"]
        access(sid, "admin")
        if not 1 <= n <= 4:
            error("Step not found.", 404)
        d = data()
        why = reason(d)
        v, c = cfg()
        if r["config_version"] != v:
            error("Create a new run for the approved configuration version.", 409)
        snap = one("SELECT * FROM snapshots WHERE id=?", (r["snapshot_id"],))
        latest = one(
            "SELECT id FROM snapshots WHERE student_id=? ORDER BY version DESC LIMIT 1", (sid,)
        )
        if (
            not snapshot_current(r)
            or snap["id"] != latest["id"]
            or readiness(sid, c)
            or mapping_gaps(c, n)
        ):
            error(
                "This run cannot execute until its specification, snapshot and readiness are current.",
                409,
            )
        previous = latest_step(rid, n - 1) if n > 1 else None
        if n > 1 and (not previous or previous["status"] != "valid"):
            error("Complete the previous mapping step first.", 409)
        old = latest_step(rid, n)
        if str(d.get("expected_attempt", 0)) != str(old["attempt"] if old else 0):
            error("Step changed. Inspect the latest attempt before retrying.", 409)
        snapshot_inputs = json.loads(snap["inputs"])
        from .mindpal import intake_context

        spec = private_mapping_spec(c)
        incoming = {
            "snapshot": snapshot_inputs,
            "upstream": {str(k): json.loads(latest_step(rid, k)["output"]) for k in range(1, n)},
            "intake_fields": intake_context(snapshot_inputs, spec) if spec else {},
            "upstream_attempts": {str(k): latest_step(rid, k)["attempt"] for k in range(1, n)},
        }
        attempt = (old["attempt"] if old else 0) + 1
        invalidate(sid, "Workflow step rerun: " + why, rid, n)
        status = "valid"
        failure = None
        out = d.get("output")
        summary = d.get("summary", "")
        if not provider_generation and (
            not isinstance(summary, str) or not summary.strip() or len(summary) > 20000
        ):
            error("An inspectable transformation summary is required.")
        unavailable = False
        if provider_generation:
            if packed(incoming) != g.generated_input:
                error(
                    "Inputs or upstream attempts changed during generation. Review and retry.", 409
                )
            out, summary, failure, unavailable = g.generated_result
            if failure:
                d["provider_error"] = failure
        if d.get("provider_error"):
            status = "blocked" if unavailable else "failed"
            failure = str(d["provider_error"])[:2000]
            out = None
        else:
            try:
                validate_output(n, c, out, json.loads(snap["inputs"])["evidence"])
            except ValueError as e:
                status = "invalid"
                failure = str(e)
                out = None
        db().execute(
            "INSERT INTO steps(run_id,step,attempt,status,input,output,summary,error,created) VALUES(?,?,?,?,?,?,?,?,?)",
            (
                rid,
                n,
                attempt,
                status,
                packed(incoming),
                packed(out) if out is not None else None,
                summary,
                failure,
                now(),
            ),
        )
        complete = all((latest_step(rid, k) or {}).get("status") == "valid" for k in range(1, 5))
        run_status = (
            "complete"
            if complete
            else (
                "blocked" if status == "blocked" else ("failed" if status != "valid" else "pending")
            )
        )
        db().execute("UPDATE runs SET status=? WHERE id=?", (run_status, rid))
        audit("step-" + status, sid, rid, why)
        return response(
            {"status": status, "attempt": attempt, "error": failure, "run_status": run_status}, sid
        )

    @app.post("/api/admin/runs/<int:rid>/generate/<int:n>")
    def generate(rid, n):
        # Provider I/O occurs outside a write transaction. Revalidate everything atomically afterwards.
        from .mindpal import intake_context
        from .provider import ProviderFailure, ProviderUnavailable, configured_provider

        r = run_record(rid)
        access(r["student_id"], "admin")
        if not 1 <= n <= 4:
            error("Step not found.", 404)
        d = data()
        reason(d)
        v, c = cfg()
        snap = one("SELECT * FROM snapshots WHERE id=?", (r["snapshot_id"],))
        if (
            r["config_version"] != v
            or not snapshot_current(r)
            or readiness(r["student_id"], c)
            or mapping_gaps(c, n)
        ):
            error(
                "Current source-backed readiness and this step's specification are required.", 409
            )
        old = latest_step(rid, n)
        if str(d.get("expected_attempt", 0)) != str(old["attempt"] if old else 0):
            error("Inspect the latest attempt before retrying.", 409)
        upstream = {str(k): latest_step(rid, k) for k in range(1, n)}
        if any(not value or value["status"] != "valid" for value in upstream.values()):
            error("Complete the prior mapping steps first.", 409)
        spec = private_mapping_spec(c)
        snapshot_inputs = json.loads(snap["inputs"])
        incoming = {
            "snapshot": snapshot_inputs,
            "upstream": {key: json.loads(value["output"]) for key, value in upstream.items()},
            "intake_fields": intake_context(snapshot_inputs, spec) if spec else {},
            "upstream_attempts": {key: value["attempt"] for key, value in upstream.items()},
        }
        g.generated_input = packed(incoming)
        try:
            provider = app.config["MAPPING_PROVIDER"] or configured_provider()
            output = provider.generate(
                n, incoming, dict(spec or {}, output_schema=step_schema(n, c))
            )
            g.generated_result = (
                output,
                "Structured output generated from the recorded snapshot and validated upstream steps; human review required.",
                None,
                False,
            )
        except (ProviderUnavailable, ProviderFailure) as exc:
            g.generated_result = (
                None,
                "No valid provider output produced; inspect prerequisites before retrying.",
                str(exc),
                isinstance(exc, ProviderUnavailable),
            )
        return record_step(rid, n, provider_generation=True)

    @app.post("/api/admin/runs/<int:rid>/reports")
    @transaction
    def draft_report(rid):
        r = run_record(rid)
        sid = r["student_id"]
        access(sid, "admin")
        d = data()
        why = reason(d)
        c = current_run(r)
        if r["status"] != "complete":
            error("All four steps must have valid current outputs.", 409)
        origin = "admin-edited"
        if d.get("from_workflow") in (True, "1"):
            from .mindpal import report_draft

            outputs = {n: json.loads(latest_step(rid, n)["output"]) for n in range(1, 5)}
            maps = validate_maps(
                c,
                report_draft(
                    outputs, concise=c.get("mapping_profile", {}).get("kind") == "3du-standalone"
                ),
            )
            origin = "generated"
        else:
            maps = validate_maps(c, d.get("maps"))
        version = one(
            "SELECT COALESCE(MAX(version),0)+1 AS v FROM reports WHERE student_id=?", (sid,)
        )["v"]
        nid = (
            db()
            .execute(
                "INSERT INTO reports(student_id,run_id,version,origin,maps,status,created) VALUES(?,?,?,?,?,'draft',?)",
                (sid, rid, version, origin, packed(maps), now()),
            )
            .lastrowid
        )
        audit("report-draft-created", sid, nid, why)
        return response({"id": nid, "version": version, "status": "draft"}, sid)

    @app.post("/api/admin/reports/<int:rid>/edit")
    @transaction
    def edit_report(rid):
        r = report_record(rid)
        sid = r["student_id"]
        access(sid, "admin")
        d = data()
        why = reason(d)
        run = run_record(r["run_id"])
        c = current_run(run)
        if run["status"] != "complete":
            error("Rerun affected workflow steps before revising the report.", 409)
        if d.get("browser_editor") in ("1", True):
            if not str(d.get("expected_version", "")).isdigit():
                error("Invalid report version.")
            d["expected_version"] = int(d["expected_version"])
            source_maps = json.loads(r["maps"])
            d["maps"] = {
                key: {
                    "summary": d.get(key + "_summary", ""),
                    "items": [
                        {"label": item["label"], "text": d.get(key + "_item_" + str(index), "")}
                        for index, item in enumerate(value["items"])
                    ],
                }
                for key, value in source_maps.items()
            }
        latest = one("SELECT MAX(version) AS v FROM reports WHERE student_id=?", (sid,))["v"]
        if d.get("expected_version") != latest or r["version"] != latest:
            error("Report changed. Review the latest version.", 409)
        maps = validate_maps(c, d.get("maps"))
        version = latest + 1
        if r["status"] == "draft":
            db().execute("UPDATE reports SET status='superseded' WHERE id=?", (rid,))
        nid = (
            db()
            .execute(
                "INSERT INTO reports(student_id,run_id,version,origin,maps,status,created) VALUES(?,?,?,'admin-edited',?,'draft',?)",
                (sid, r["run_id"], version, packed(maps), now()),
            )
            .lastrowid
        )
        audit("report-edited", sid, nid, why)
        if not request.is_json and d.get("browser_editor") == "1":
            return redirect(f"/admin/students/{sid}#reports")
        return response({"id": nid, "version": version, "approvals": []}, sid)

    @app.post("/api/reports/<int:rid>/approve")
    @transaction
    def approve_report(rid):
        r = report_record(rid)
        sid = r["student_id"]
        access(sid, "admin", "mentor")
        d = data()
        why = reason(d)
        valid_report(r)
        if d.get("version") != r["version"]:
            error("Approval must reference the exact reviewed version.", 409)
        role = g.user["role"]
        if cfg()[1].get("mapping_profile", {}).get("kind") == "3du-standalone" and any(
            "requires admin editing before approval"
            in json.loads(r["maps"])[role_name + "_journey"]["summary"]
            for role_name in ["student", "parent"]
        ):
            error("Write and review both concise journey summaries before approval.", 409)
        if role == "admin" and d.get("wording_reviewed") is not True:
            error("Review shared wording for both student and parent before approving.", 409)
        if role == "mentor":
            if one("SELECT id FROM publications WHERE student_id=?", (sid,)):
                error("Fresh mentor approval is only required for the initial report.", 409)
            if not one(
                "SELECT a.actor_id FROM approvals a JOIN relationships rel ON rel.actor_id=a.actor_id AND rel.student_id=? AND rel.kind='admin' WHERE a.report_id=? AND a.role='admin'",
                (sid, rid),
            ):
                error("Admin approval of this exact version is required first.", 409)
        db().execute(
            "INSERT OR IGNORE INTO approvals VALUES(?,?,?,?,?)",
            (rid, g.user["id"], role, why, now()),
        )
        audit("report-" + role + "-approval", sid, rid, why)
        return response({"status": "approved", "version": r["version"]}, sid)

    @app.post("/api/admin/reports/<int:rid>/publish")
    @transaction
    def publish(rid):
        r = report_record(rid)
        sid = r["student_id"]
        access(sid, "admin")
        d = data()
        why = reason(d)
        if d.get("version") != r["version"]:
            error("Publication must reference the exact version.", 409)
        if one("SELECT id FROM publications WHERE report_id=?", (rid,)):
            return response({"status": "published", "version": r["version"], "repeated": True}, sid)
        valid_report(r)
        if not one(
            "SELECT a.actor_id FROM approvals a JOIN relationships rel ON rel.actor_id=a.actor_id AND rel.student_id=? AND rel.kind='admin' WHERE a.report_id=? AND a.role='admin'",
            (sid, rid),
        ):
            error("Current admin approval of this version is required.", 409)
        initial = not one("SELECT id FROM publications WHERE student_id=?", (sid,))
        if initial and not one(
            "SELECT a.actor_id FROM approvals a JOIN relationships rel ON rel.actor_id=a.actor_id AND rel.student_id=? AND rel.kind='mentor' WHERE a.report_id=? AND a.role='mentor'",
            (sid, rid),
        ):
            error(
                "An involved mentor must approve this same initial version. There is no bypass.",
                409,
            )
        latest = one(
            "SELECT r.version FROM publications p JOIN reports r ON r.id=p.report_id WHERE p.student_id=? ORDER BY p.id DESC LIMIT 1",
            (sid,),
        )
        if latest and latest["version"] >= r["version"]:
            error("An earlier version cannot replace a later publication.", 409)
        db().execute(
            "INSERT INTO publications(student_id,report_id,actor_id,created) VALUES(?,?,?,?)",
            (sid, rid, g.user["id"], now()),
        )
        db().execute("UPDATE reports SET status='published' WHERE id=?", (rid,))
        audit("report-published", sid, rid, why)
        return response({"status": "published", "version": r["version"]}, sid)

    @app.get("/mentor/students/<int:sid>")
    def mentor_workspace(sid):
        access(sid, "mentor")
        scopes = mentor_scope(sid)["stages"]
        relevant = [
            dict(
                number=n,
                name=STAGES[n - 1],
                draft=packed(mentor_work(sid, n)["draft"]),
                status=stage(sid, n)["status"],
                revision=stage(sid, n)["revision"],
            )
            for n in scopes
        ]
        reports = []
        if not one("SELECT id FROM publications WHERE student_id=?", (sid,)):
            for r in rows(
                "SELECT id,version,maps FROM reports WHERE student_id=? AND status='draft' ORDER BY version DESC",
                (sid,),
            ):
                if one(
                    "SELECT actor_id FROM approvals WHERE report_id=? AND role='admin'", (r["id"],)
                ):
                    r["maps"] = json.loads(r["maps"])
                    reports.append(r)
        return render_template(
            "mentor.html",
            sid=sid,
            work=relevant,
            reports=reports,
            mentor_inputs_enabled=cfg()[1].get("mapping_profile", {}).get("kind")
            == "3du-standalone",
            notes=rows(
                "SELECT * FROM notes WHERE student_id=? AND actor_id=? AND kind='session'",
                (sid, g.user["id"]),
            ),
        )

    @app.get("/api/mentor/students/<int:sid>")
    def mentor_data(sid):
        access(sid, "mentor")
        scopes = mentor_scope(sid)["stages"]
        work = [mentor_work(sid, n) for n in scopes]
        return jsonify(
            work=work,
            sessions=rows(
                "SELECT id,text,created FROM notes WHERE student_id=? AND actor_id=? AND kind='session'",
                (sid, g.user["id"]),
            ),
        )

    @app.post("/api/students/<int:sid>/notes")
    @transaction
    def add_note(sid):
        access(sid, "admin", "mentor")
        d = data()
        why = reason(d)
        validate(
            obj(
                {
                    "kind": {"enum": ["session", "information-request"]},
                    "text": SHORT,
                    "reason": SHORT,
                }
            ),
            d,
        )
        if g.user["role"] == "mentor" and d["kind"] != "session":
            error("Only the team can request information.", 403)
        nid = (
            db()
            .execute(
                "INSERT INTO notes(student_id,actor_id,kind,text,created) VALUES(?,?,?,?,?)",
                (sid, g.user["id"], d["kind"], d["text"], now()),
            )
            .lastrowid
        )
        audit("note-" + d["kind"], sid, nid, why)
        return (
            response({"id": nid}, sid)
            if g.user["role"] == "admin"
            else (
                jsonify(id=nid)
                if request.is_json
                else redirect(url_for("mentor_workspace", sid=sid))
            )
        )

    def imported_spec_by_hash(source_hash):
        if not source_hash:
            return None
        record = one(
            "SELECT normalized_json FROM mapping_imports WHERE source_sha256=? ORDER BY id DESC LIMIT 1",
            (source_hash,),
        )
        return json.loads(record["normalized_json"]) if record else None

    def private_mapping_spec(c):
        return imported_spec_by_hash(c.get("mapping_profile", {}).get("source_sha256"))

    @app.get("/api/admin/mapping-specification")
    def mapping_specification():
        need_role("admin")
        _, c = cfg()
        return jsonify(specification=private_mapping_spec(c), gaps=mapping_gaps(c))

    @app.cli.command("import-mindpal")
    @click.argument("path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
    @click.option("--mapping-prompt", type=click.Path(exists=True, dir_okay=False, path_type=Path))
    @click.option("--actor-email", required=True)
    @click.option("--reason", "why", required=True)
    def import_mindpal(path, mapping_prompt, actor_email, why):
        from .mindpal import parse_export

        actor = one("SELECT * FROM users WHERE email=? AND role='admin'", (actor_email,))
        if not actor or not why.strip() or len(why) > 2000:
            raise click.ClickException("Existing admin and a review reason are required.")
        try:
            raw = path.read_bytes()
            spec = parse_export(raw)
            prompt_raw = mapping_prompt.read_bytes() if mapping_prompt else None
            if prompt_raw is not None:
                from .mindpal import supplement_mapping

                spec = supplement_mapping(spec, prompt_raw)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        g.user = actor
        if cfg()[1].get("mapping_profile", {}).get("kind") == "3du-standalone":
            raise click.ClickException(
                "Use import-3du-mapping for the active standalone installation."
            )
        db().execute("BEGIN IMMEDIATE")
        try:
            v, c = cfg()
            if c.get("mapping_profile", {}).get("source_sha256") == spec["sha256"]:
                db().execute("COMMIT")
                click.echo("This exact export is already imported; configuration unchanged.")
                return
            for key in [
                "student_personas",
                "parent_personas",
                "empathy_categories",
                "journey_fields",
            ]:
                c[key] = spec[key] + (
                    ["human intervention"] if key == "journey_fields" and not prompt_raw else []
                )
            c["journey_stages"] = spec["journey_stages"]
            if prompt_raw:
                c["mapping_details"] = {
                    key: spec[key]
                    for key in ["evidence_types", "persona_details", "empathy_factors"]
                }
            else:
                c.pop("mapping_details", None)
            c["mapping_profile"] = {"kind": "mindpal-four-step", "source_sha256": spec["sha256"]}
            config_validate(c)
            db().execute(
                "INSERT INTO mapping_imports(config_version,source_sha256,source_json,source_prompt,normalized_json,actor_id,reason,created) VALUES(?,?,?,?,?,?,?,?)",
                (
                    v + 1,
                    spec["sha256"],
                    raw.decode(),
                    prompt_raw.decode("utf-8-sig") if prompt_raw else None,
                    packed(spec),
                    actor["id"],
                    why.strip(),
                    now(),
                ),
            )
            db().execute("UPDATE settings SET version=version+1,body=? WHERE id=1", (packed(c),))
            for student in rows("SELECT id FROM users WHERE role='student'"):
                invalidate(student["id"], "Imported source mapping configuration: " + why)
            audit("mapping-specification-import", None, v + 1, why)
            db().execute("COMMIT")
        except BaseException:
            db().execute("ROLLBACK")
            raise
        click.echo(
            "Imported private four-step instructions and supplied enumerations. Full mapping gaps: "
            + ", ".join(mapping_gaps(c))
            + ". Readiness/provider/policy requirements still apply. Scoring/matching branches remain disabled."
        )

    def setup_access():
        need_role("admin")
        if not one(
            "SELECT actor_id FROM admin_capabilities WHERE actor_id=? AND capability='mapping_setup'",
            (g.user["id"],),
        ):
            error("Mapping setup requires a separately provisioned capability.", 403)

    @app.cli.command("grant-mapping-setup")
    @click.option("--actor-email", required=True)
    @click.option("--authorized-by", required=True)
    @click.option("--reason", "why", required=True)
    def grant_mapping_setup(actor_email, authorized_by, why):
        actor = one("SELECT * FROM users WHERE email=? AND role='admin'", (actor_email,))
        owner = one("SELECT * FROM users WHERE email=? AND role='admin'", (authorized_by,))
        if not actor or not owner or not why.strip():
            raise click.ClickException(
                "Existing admin accounts and an authorization reason required."
            )
        # Trusted host-console provisioning; no public capability-grant endpoint exists.
        g.user = owner
        db().execute("BEGIN IMMEDIATE")
        try:
            db().execute(
                "INSERT OR IGNORE INTO admin_capabilities VALUES(?,'mapping_setup',?,?,?)",
                (actor["id"], owner["id"], why, now()),
            )
            audit("grant-mapping-setup", None, actor["id"], why)
            db().execute("COMMIT")
        except BaseException:
            db().execute("ROLLBACK")
            raise
        click.echo(
            "Mapping setup capability provisioned. Educator/live-data permissions are not granted."
        )

    def activate_standalone(raw, actor, why):
        from .standalone import apply_to_config, parse_configuration

        spec = parse_configuration(raw)
        v, c = cfg()
        if c.get("mapping_profile", {}).get("source_sha256") == spec["sha256"]:
            return {"version": v, "repeated": True}
        c = config_validate(apply_to_config(c, spec))
        db().execute(
            "INSERT INTO mapping_imports(config_version,source_sha256,source_json,normalized_json,actor_id,reason,created) VALUES(?,?,?,?,?,?,?)",
            (v + 1, spec["sha256"], raw.decode(), packed(spec), actor["id"], why, now()),
        )
        db().execute("UPDATE settings SET version=version+1,body=? WHERE id=1", (packed(c),))
        for student in rows("SELECT id FROM users WHERE role='student'"):
            invalidate(student["id"], "Standalone configuration activated: " + why)
        audit("standalone-configuration-activated", None, v + 1, why)
        return {"version": v + 1}

    @app.cli.command("import-3du-mapping")
    @click.argument("path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
    @click.option("--actor-email", required=True)
    @click.option("--reason", "why", required=True)
    def import_3du_mapping(path, actor_email, why):
        actor = one("SELECT * FROM users WHERE email=? AND role='admin'", (actor_email,))
        if (
            not actor
            or not one(
                "SELECT actor_id FROM admin_capabilities WHERE actor_id=? AND capability='mapping_setup'",
                (actor["id"],),
            )
            or not why.strip()
        ):
            raise click.ClickException(
                "Provisioned mapping-setup admin and authorization reason required."
            )
        g.user = actor
        db().execute("BEGIN IMMEDIATE")
        try:
            result = activate_standalone(path.read_bytes(), actor, why)
            db().execute("COMMIT")
        except BaseException as exc:
            db().execute("ROLLBACK")
            raise click.ClickException(str(exc)) from exc
        click.echo(
            "Independent 3DU configuration active, version "
            + str(result["version"])
            + ". Readiness/provider/policy blockers still apply."
        )

    @app.get("/admin/setup/mapping")
    def standalone_setup():
        setup_access()
        return render_template(
            "mapping_setup.html",
            drafts=rows(
                "SELECT id,base_version,state,actor_id,approved_by,reason,created FROM mapping_configuration_drafts ORDER BY id DESC"
            ),
            config_version=cfg()[0],
        )

    @app.post("/api/admin/setup/mapping")
    @transaction
    def standalone_upload():
        setup_access()
        from .standalone import parse_configuration

        why = reason(data())
        upload = request.files.get("configuration")
        if not upload:
            error("Choose the private standalone JSON file.")
        raw = upload.read()
        spec = parse_configuration(raw)
        identifier = (
            db()
            .execute(
                "INSERT INTO mapping_configuration_drafts(source_json,source_sha256,base_version,state,actor_id,reason,created) VALUES(?,?,?,'draft',?,?,?)",
                (raw.decode(), spec["sha256"], cfg()[0], g.user["id"], why, now()),
            )
            .lastrowid
        )
        audit("standalone-configuration-draft", None, identifier, why)
        return redirect(url_for("standalone_setup"))

    @app.post("/api/admin/setup/mapping/<int:identifier>/<action>")
    @transaction
    def standalone_transition(identifier, action):
        setup_access()
        from .standalone import parse_configuration

        why = reason(data())
        record = one("SELECT * FROM mapping_configuration_drafts WHERE id=?", (identifier,))
        if not record:
            error("Configuration draft not found.", 404)
        transitions = {
            "validate": ("draft", "validated"),
            "approve": ("validated", "approved"),
            "activate": ("approved", "active"),
        }
        if action not in transitions or record["state"] != transitions[action][0]:
            error("Configuration state changed. Reload and review.", 409)
        if record["base_version"] != cfg()[0]:
            error("The active configuration changed. Upload a new draft for review.", 409)
        parse_configuration(record["source_json"].encode())
        if action == "approve" and request.form.get("owner_approved") != "yes":
            error("Record authorized owner approval before activation.")
        if action == "activate":
            activate_standalone(record["source_json"].encode(), g.user, why)
        db().execute(
            "UPDATE mapping_configuration_drafts SET state=?,approved_by=CASE WHEN ? THEN ? ELSE approved_by END WHERE id=?",
            (transitions[action][1], action == "approve", g.user["id"], identifier),
        )
        audit("standalone-configuration-" + action, None, identifier, why)
        return redirect(url_for("standalone_setup"))

    @app.route("/mentor/students/<int:sid>/inputs", methods=["GET", "POST"])
    @transaction
    def mentor_inputs(sid):
        access(sid, "mentor")
        if cfg()[1].get("mapping_profile", {}).get("kind") != "3du-standalone":
            error("Professional input is waiting for standalone configuration.", 409)
        entry = one(
            "SELECT * FROM professional_entries WHERE student_id=? AND actor_id=?",
            (sid, g.user["id"]),
        )
        if request.method == "GET":
            return render_template("professional_input.html", sid=sid, entry=entry)
        d = data()
        if d.get("action") not in ["save", "submit"]:
            error("Choose Save draft or Submit.")
        expected = str(d.get("expected_version", ""))
        if not expected.isdigit() or int(expected) != (entry["version"] if entry else 0):
            error("Your notes changed. Reload and review.", 409)
        values = {k: d.get(k, "") for k in ["Mentor Notes", "Previous Interaction Notes"]}
        if any(not isinstance(x, str) or len(x) > 20000 for x in values.values()):
            error("Notes must be text of at most 20,000 characters.")
        submitted = d["action"] == "submit"
        if submitted and not values["Mentor Notes"].strip():
            error("Mentor Notes are required before submission.")
        if not entry:
            identifier = (
                db()
                .execute(
                    "INSERT INTO professional_entries(student_id,actor_id,updated) VALUES(?,?,?)",
                    (sid, g.user["id"], now()),
                )
                .lastrowid
            )
            entry = one("SELECT * FROM professional_entries WHERE id=?", (identifier,))
        version = entry["version"] + 1
        db().execute(
            "UPDATE professional_entries SET draft=?,version=?,updated=?,submitted=CASE WHEN ? THEN ? ELSE submitted END WHERE id=?",
            (packed(values), version, now(), submitted, packed(values), entry["id"]),
        )
        if submitted:
            db().execute(
                "INSERT INTO professional_versions VALUES(?,?,?,?)",
                (entry["id"], version, packed(values), now()),
            )
            # Use the same source-attribution convention as student/parent evidence.
            spec = private_mapping_spec(cfg()[1])
            for label, statement in values.items():
                source = f"Intake: {label} [actor={g.user['id']};spec={spec['sha256']}]"
                old = one(
                    "SELECT id FROM evidence WHERE student_id=? AND source=? AND NOT EXISTS(SELECT 1 FROM evidence newer WHERE newer.corrected_from=evidence.id) ORDER BY id DESC LIMIT 1",
                    (sid, source),
                )
                db().execute(
                    "INSERT INTO evidence(student_id,stakeholder,source,type,statement,corrected_from) VALUES(?,?,?,?,?,?)",
                    (
                        sid,
                        "mentor",
                        source,
                        "mentor note" if label == "Mentor Notes" else "previous interaction note",
                        statement,
                        old["id"] if old else None,
                    ),
                )
            invalidate(sid, "Mentor submitted attributable notes; new snapshot required.")
        audit("professional-input-" + d["action"], sid, entry["id"], "Own involved-mentor input")
        return redirect(url_for("mentor_inputs", sid=sid))

    def own_intake(sid):
        access(sid, "student", "parent")
        if g.user["role"] == "student" and not unlocked(sid, 1):
            error(LOCKED, 403)
        _, c = cfg()
        spec = private_mapping_spec(c)
        from .mindpal import PARENT_FIELDS, STUDENT_FIELDS

        allowed = STUDENT_FIELDS if g.user["role"] == "student" else PARENT_FIELDS
        # Confirmed form fields work independently of private AI configuration.
        fields = (
            [f for f in spec["fields"] if f["label"] in allowed]
            if spec
            else [
                {
                    "id": label.lower().replace(" ", "_"),
                    "label": label,
                    "type": "TEXT",
                    "required": True,
                }
                for label in allowed
            ]
        )
        entry = one(
            "SELECT * FROM intake_entries WHERE student_id=? AND actor_id=?", (sid, g.user["id"])
        )
        return entry, fields, allowed

    def intake_view(sid):
        entry, fields, _ = own_intake(sid)
        entry = entry or {
            "id": None,
            "version": 0,
            "draft": "{}",
            "submissions": 0,
            "submitted": None,
        }
        return {
            "sid": sid,
            "entry": entry,
            "fields": fields,
            "request_key": secrets.token_urlsafe(24),
            "legacy_profile_note": (
                one("SELECT note FROM profile_legacy_notes WHERE student_id=?", (sid,)) or {}
            ).get("note", "")
            if g.user["role"] == "student"
            else "",
            "read_only": entry["submissions"] >= 2
            or (g.user["role"] == "student" and stage(sid, 1)["status"] == "complete"),
        }

    @app.get("/students/<int:sid>/intake")
    def intake_page(sid):
        return render_template("intake.html", **intake_view(sid))

    @app.route("/api/students/<int:sid>/intake", methods=["GET", "POST"])
    @transaction
    def intake_api(sid):
        entry, fields, allowed = own_intake(sid)
        if request.method == "GET":
            return jsonify(entry=entry, fields=fields)
        if not request.is_json and not request.form.get("expected_version", "0").isdigit():
            error("Invalid saved-entry version.")
        d = (
            data()
            if request.is_json
            else {
                "action": request.form.get("action"),
                "expected_version": int(request.form.get("expected_version", "0")),
                "request_key": request.form.get("request_key"),
                "values": {key: request.form.get(key, "") for key in allowed},
            }
        )
        validate(
            obj(
                {
                    "action": {"enum": ["save", "submit"]},
                    "expected_version": {"type": "integer", "minimum": 0},
                    "request_key": SHORT,
                    "values": obj({key: TEXT for key in allowed}, required=[]),
                }
            ),
            d,
        )
        if not entry:
            db().execute(
                "INSERT INTO intake_entries(student_id,actor_id,role,config_version,updated) VALUES(?,?,?,?,?)",
                (sid, g.user["id"], g.user["role"], cfg()[0], now()),
            )
            entry = one(
                "SELECT * FROM intake_entries WHERE student_id=? AND actor_id=?",
                (sid, g.user["id"]),
            )
        duplicate = one(
            "SELECT fingerprint,result FROM intake_requests WHERE entry_id=? AND request_key=?",
            (entry["id"], d["request_key"]),
        )
        fingerprint = digest(packed(d))
        if duplicate:
            if duplicate["fingerprint"] != fingerprint:
                error(
                    "This request key was used for different content. Reload and review your saved entry.",
                    409,
                )
            return (
                jsonify(json.loads(duplicate["result"]))
                if request.is_json
                else redirect(url_for("intake_page", sid=sid))
            )
        if entry["submissions"] >= 2:
            error(
                "Your one resubmission has been used. Contact the team for an audited correction.",
                409,
            )
        if entry["version"] != d["expected_version"]:
            error("Your saved entry changed. Reload before editing.", 409)
        if g.user["role"] == "student" and stage(sid, 1)["status"] == "complete":
            error("Completed work is read-only. Ask admin for an audited correction.", 409)
        if d["action"] == "submit" and any(
            f["required"] and not d["values"].get(f["label"], "").strip() for f in fields
        ):
            error(
                "Complete required fields: "
                + ", ".join(
                    f["label"]
                    for f in fields
                    if f["required"] and not d["values"].get(f["label"], "").strip()
                )
            )
        version = entry["version"] + 1
        submitted = d["action"] == "submit"
        db().execute(
            "UPDATE intake_entries SET config_version=?,draft=?,version=?,updated=?,submitted=CASE WHEN ? THEN ? ELSE submitted END,submitted_version=CASE WHEN ? THEN ? ELSE submitted_version END,submissions=submissions+? WHERE id=?",
            (
                cfg()[0],
                packed(d["values"]),
                version,
                now(),
                submitted,
                packed(d["values"]),
                submitted,
                version,
                submitted,
                entry["id"],
            ),
        )
        if g.user["role"] == "student" and (submitted or entry["submissions"] == 0):
            legacy = json.loads(stage(sid, 1)["draft"]).get("reflection", "")
            if isinstance(legacy, str) and legacy:
                db().execute(
                    "INSERT OR IGNORE INTO profile_legacy_notes VALUES(?,?,?)", (sid, legacy, now())
                )
            # Stage 1 reviews the actual submitted form. Later unsent revision drafts stay private.
            db().execute(
                "UPDATE stages SET draft=?,status=?,revision=revision+1 WHERE student_id=? AND stage=1",
                (packed(d["values"]), "submitted" if submitted else "draft", sid),
            )
            if not submitted:
                invalidate(sid, "Profile draft changed; previous snapshots require review.")
        if submitted:
            db().execute(
                "INSERT INTO intake_versions VALUES(?,?,?,?,?)",
                (entry["id"], version, cfg()[0], packed(d["values"]), now()),
            )
            for label in set(d["values"]) | set(json.loads(entry["submitted"] or "{}")):
                value = d["values"].get(label, "")
                old = one(
                    "SELECT evidence_id FROM intake_evidence WHERE entry_id=? AND field=?",
                    (entry["id"], label),
                )
                previous = old["evidence_id"] if old else None
                # Admin may have corrected this source since the user's prior submission.
                while previous and (
                    newer := one("SELECT id FROM evidence WHERE corrected_from=?", (previous,))
                ):
                    previous = newer["id"]
                revision = (
                    (one("SELECT revision FROM evidence WHERE id=?", (previous,))["revision"] + 1)
                    if previous
                    else 1
                )
                eid = (
                    db()
                    .execute(
                        "INSERT INTO evidence(student_id,stakeholder,source,type,statement,revision,corrected_from) VALUES(?,?,?,?,?,?,?)",
                        (
                            sid,
                            g.user["role"],
                            "Intake: " + label + " [actor=" + str(g.user["id"]) + "]",
                            allowed[label] if value.strip() else "missing evidence",
                            value,
                            revision,
                            previous,
                        ),
                    )
                    .lastrowid
                )
                db().execute(
                    "INSERT INTO intake_evidence VALUES(?,?,?) ON CONFLICT(entry_id,field) DO UPDATE SET evidence_id=excluded.evidence_id",
                    (entry["id"], label, eid),
                )
            invalidate(sid, "Submitted intake changed; save and review a new mapping snapshot.")
        result = {
            "id": entry["id"],
            "version": version,
            "status": "submitted" if submitted else "draft",
            "submissions": entry["submissions"] + int(submitted),
        }
        db().execute(
            "INSERT INTO intake_requests VALUES(?,?,?,?)",
            (entry["id"], d["request_key"], fingerprint, packed(result)),
        )
        audit(
            "intake-" + d["action"],
            sid,
            entry["id"],
            "Own attributed intake; no stage completion or report publication",
        )
        return jsonify(result) if request.is_json else redirect(url_for("intake_page", sid=sid))

    @app.cli.command("backup-db")
    def backup_db():
        """Consistent SQLite backup including committed WAL data; trusted host console."""
        folder = Path(app.config["DATABASE"]).parent / "backups"
        folder.mkdir(mode=0o700, parents=True, exist_ok=True)
        target = folder / (
            "3du-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f") + ".sqlite3"
        )
        connection = sqlite3.connect(target)
        try:
            db().backup(connection)
        finally:
            connection.close()
        os.chmod(target, 0o600)
        click.echo("Private database backup saved: " + str(target))

    @app.cli.command("init-db")
    def init_db():
        conn = db()
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, applied TEXT NOT NULL)"
        )
        for path in sorted((ROOT / "migrations").glob("*.sql")):
            version = int(path.name.split("_")[0])
            if not one("SELECT version FROM schema_migrations WHERE version=?", (version,)):
                conn.executescript(
                    "BEGIN IMMEDIATE;\n"
                    + path.read_text()
                    + f"\nINSERT INTO schema_migrations VALUES({version},'{now()}');\nCOMMIT;"
                )
        conn.execute("INSERT OR IGNORE INTO settings VALUES(1,1,?)", (packed(DEFAULT_CONFIG),))
        conn.execute("PRAGMA journal_mode=WAL")
        click.echo("Database migrations applied.")

    @app.cli.command("provision")
    @click.option("--email", required=True)
    @click.option(
        "--role", type=click.Choice(["student", "parent", "mentor", "admin"]), required=True
    )
    @click.option("--reason", required=True)
    @click.password_option(confirmation_prompt=True)
    def provision(email, role, reason, password):
        if not app.config["SYNTHETIC_ONLY"]:
            raise click.ClickException("Live provisioning blocked pending policy approval.")
        if len(password) < 12:
            raise click.ClickException("Password must contain at least 12 characters.")
        if one("SELECT id FROM users WHERE email=?", (email,)):
            raise click.ClickException("Account already exists; role cannot be silently changed.")
        uid = (
            db()
            .execute(
                "INSERT INTO users(email,password,role) VALUES(?,?,?)",
                (email.lower(), generate_password_hash(password), role),
            )
            .lastrowid
        )
        if role == "student":
            db().executemany(
                "INSERT INTO stages(student_id,stage) VALUES(?,?)", [(uid, n) for n in range(1, 9)]
            )
        db().execute(
            "INSERT INTO audit(action,record_id,reason,created) VALUES(?,?,?,?)",
            ("operator-provision-" + role, uid, reason, now()),
        )
        click.echo(f"Provisioned {role} account ID {uid}. Synthetic development only.")

    @app.cli.command("authorize")
    @click.option("--actor-email", required=True)
    @click.option("--student-email", required=True)
    @click.option(
        "--scopes",
        default="",
        help="Approved mentor stage numbers, comma separated; empty means no raw work access.",
    )
    @click.option(
        "--fields",
        default="{}",
        help='Approved mentor draft-field scope JSON, e.g. {"6":["reflection"]}. Empty by default.',
    )
    @click.option("--reason", required=True)
    def authorize(actor_email, student_email, scopes, fields, reason):
        a = one("SELECT * FROM users WHERE email=?", (actor_email,))
        s = one("SELECT * FROM users WHERE email=?", (student_email,))
        if (
            not a
            or not s
            or s["role"] != "student"
            or a["role"] not in ("parent", "mentor", "admin")
        ):
            raise click.ClickException(
                "Existing authorized actor and student accounts are required."
            )
        try:
            ns = [int(n) for n in scopes.split(",") if n]
        except ValueError:
            raise click.ClickException("Scopes must be stage numbers.")
        if any(n < 1 or n > 8 for n in ns) or (ns and a["role"] != "mentor"):
            raise click.ClickException("Only mentor stage scopes 1–8 are supported.")
        try:
            fs = json.loads(fields)
            validate(
                {
                    "type": "object",
                    "patternProperties": {"^[1-8]$": STRINGS},
                    "additionalProperties": False,
                },
                fs,
            )
        except ValueError as e:
            raise click.ClickException(str(e))
        if any(int(k) not in ns for k in fs):
            raise click.ClickException("Field access must be within approved stage scopes.")
        scope = {"stages": sorted(set(ns)), "fields": fs} if a["role"] == "mentor" else []
        db().execute(
            "INSERT OR REPLACE INTO relationships VALUES(?,?,?,?)",
            (a["id"], s["id"], a["role"], packed(scope)),
        )
        db().execute(
            "INSERT INTO audit(actor_id,student_id,action,reason,created) VALUES(?,?,?,?,?)",
            (a["id"], s["id"], "operator-authorize-" + a["role"], reason, now()),
        )
        click.echo(
            "Relationship recorded. This operator command is not a guardian-verification policy."
        )

    @app.cli.command("revoke")
    @click.option("--actor-email", required=True)
    @click.option("--student-email", required=True)
    @click.option("--reason", required=True)
    def revoke(actor_email, student_email, reason):
        a = one("SELECT * FROM users WHERE email=?", (actor_email,))
        s = one("SELECT * FROM users WHERE email=?", (student_email,))
        if not a or not s:
            raise click.ClickException("Accounts not found.")
        db().execute(
            "DELETE FROM relationships WHERE actor_id=? AND student_id=?", (a["id"], s["id"])
        )
        db().execute(
            "INSERT INTO audit(actor_id,student_id,action,reason,created) VALUES(?,?,?,?,?)",
            (a["id"], s["id"], "operator-revoke", reason, now()),
        )
        click.echo("Relationship revoked.")

    return app
