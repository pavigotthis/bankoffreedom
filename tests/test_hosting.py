import importlib.util
from pathlib import Path


def load_wsgi(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "hosted.sqlite3"))
    monkeypatch.setenv("RECOVERY_DIR", str(tmp_path / "recovery"))
    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    monkeypatch.delenv("SYNTHETIC_ONLY", raising=False)
    spec = importlib.util.spec_from_file_location(
        "hosted_test_wsgi", Path(__file__).resolve().parents[1] / "wsgi.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.application


def test_hosted_entrypoint_secure_cookies_and_synthetic_gate(monkeypatch, tmp_path):
    app = load_wsgi(monkeypatch, tmp_path)
    assert app.config["COOKIE_SECURE"] is True
    assert app.config["SYNTHETIC_ONLY"] is True
    result = app.test_cli_runner().invoke(args=["init-db"])
    assert result.exit_code == 0
    response = app.test_client().get("/", base_url="https://synthetic.example.test")
    assert response.status_code == 200
    assert "Secure" in response.headers["Set-Cookie"]
    assert b"fictional accounts" in response.data


def test_hosted_import_does_not_seed_or_reset_database(monkeypatch, tmp_path):
    import sqlite3

    app = load_wsgi(monkeypatch, tmp_path)
    assert not Path(app.config["DATABASE"]).exists()
    assert app.test_cli_runner().invoke(args=["init-db"]).exit_code == 0
    connection = sqlite3.connect(app.config["DATABASE"])
    assert connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
    connection.execute(
        "INSERT INTO users(email,password,role) VALUES('fictional@example.test','fixture','student')"
    )
    connection.commit()
    connection.close()
    load_wsgi(monkeypatch, tmp_path)
    connection = sqlite3.connect(app.config["DATABASE"])
    assert connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
    connection.close()
