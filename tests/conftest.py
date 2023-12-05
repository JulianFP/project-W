import os
import smtplib
import sys
import flask
import pytest
from project_W import create_app
from tests import get_auth_headers

sys.path.append(os.path.join(os.path.dirname(__file__), "helpers"))

import flask_test_utils as ftu

@pytest.fixture()
def app(monkeypatch, tmp_path):
    temp_db_path = str(tmp_path)
    monkeypatch.setenv("PROJECT_W_JWT_SECRET_KEY", "abcdefghijklmnopqrstuvwxyz")
    monkeypatch.setenv("PROJECT_W_DB_PATH", temp_db_path)

    monkeypatch.setattr(
        smtplib.SMTP,
        "__init__",
        lambda self, host: print(f"Monkeypatched SMTP host: {host}", flush=True),
    )
    monkeypatch.setattr(
        smtplib.SMTP,
        "send_message",
        lambda self, msg: flask.current_app.config.update(
            TESTING_ONLY_LAST_SMTP_MESSAGE=msg
        ),
    )
    app = create_app()
    ftu.add_test_users(app)
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()

def _auth_fixture(email, password):
    @pytest.fixture()
    def auth(client):
        return get_auth_headers(client, email, password)
    return auth

user = _auth_fixture("user@test.com", "user")
admin = _auth_fixture("admin@test.com", "admin")
