import json
import secrets
import subprocess
import time

import psycopg
import pytest
import redis
import requests

BACKEND_BASE_URL = "https://localhost:8443"
CONFIG_PATH = "backend-config/config.yml"


@pytest.fixture(scope="session")
def secret_key():
    return secrets.token_hex(32)


def wait_for_backend(timeout=30):
    for _ in range(timeout):
        try:
            requests.get(f"{BACKEND_BASE_URL}/api/about", verify=False)
            return
        except requests.exceptions.RequestException:
            time.sleep(1)
    raise TimeoutError("Server did not become healthy in time.")


@pytest.fixture(scope="function")
def backend(request, smtpd, secret_key):
    postgres_conn = "postgresql://test:test@localhost:5432/test_db"
    redis_conn = "redis://localhost:6379/project-W"

    settings = {
        "client_url": f"{BACKEND_BASE_URL}/#",
        "web_server": {
            "port": 8443,
            "ssl": {
                "cert_file": "/etc/xdg/project-W/certs/cert.pem",
                "key_file": "/etc/xdg/project-W/certs/key.pem",
            },
        },
        "smtp_server": {
            "hostname": smtpd.hostname,
            "port": smtpd.port,
            "secure": "plain",
            "sender_email": "ci@example.org",
        },
        "postgres_connection_string": postgres_conn,
        "redis_connection": {
            "connection_string": redis_conn,
        },
        "security": {
            "local_token": {
                "session_secret_key": secret_key,
            },
            "local_account": {
                "user_provisioning": {
                    0: {
                        "email": "admin@example.org",
                        "password": "Password-1234",
                        "is_admin": True,
                    }
                },
            },
        },
        "imprint": request.param[0],
    }

    with open(CONFIG_PATH, "w") as f:
        json.dump(settings, f)

    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.ci.yml",
            "--profile",
            "app",
            "up",
            "-d",
            "project-w",
        ],
        check=True,
    )
    wait_for_backend()

    yield (f"{BACKEND_BASE_URL}/api/", smtpd)

    with psycopg.connect(postgres_conn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DROP SCHEMA project_w CASCADE
            """
            )

    r = redis.Redis()
    redis_client = r.from_url(redis_conn)
    redis_client.flushdb()
