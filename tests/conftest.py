import json
import secrets
import subprocess
import time
from pathlib import Path

import psycopg
import pytest
import redis
import requests
from pydantic import PostgresDsn, RedisDsn, SecretStr

from project_W.models.base import EmailValidated, PasswordValidated

from ..project_W.models.settings import (
    LocalAccountSettings,
    LocalTokenSettings,
    ProvisionedUser,
    RedisConnection,
    SecuritySettings,
    Settings,
    SMTPSecureEnum,
    SMTPServerSettings,
    SslSettings,
    WebServerSettings,
)

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
    smtpd.config.use_starttls = True

    postgres_connection = PostgresDsn("postgresql://test:test@localhost:5432/test_db")
    redis_connection = RedisDsn("redis://localhost:6379/project-W")

    settings: Settings = Settings(
        client_url=f"{BACKEND_BASE_URL}/#",
        web_server=WebServerSettings(
            port=8443,
            ssl=SslSettings(
                cert_file=Path("/etc/xdg/project-W/certs/cert.pem"),
                key_file=Path("/etc/xdg/project-W/certs/key.pem"),
            ),
        ),
        smtp_server=SMTPServerSettings(
            hostname=smtpd.hostname,
            port=smtpd.port,
            secure=SMTPSecureEnum.STARTTLS,
            sender_email=EmailValidated("ci@example.org"),
        ),
        postgres_connection_string=postgres_connection,
        redis_connection=RedisConnection(connection_string=redis_connection),
        security=SecuritySettings(
            local_token=LocalTokenSettings(session_secret_key=secret_key),
            local_account=LocalAccountSettings(
                user_provisioning={
                    0: ProvisionedUser(
                        email=EmailValidated("admin@example.org"),
                        password=PasswordValidated(SecretStr("Password1234")),
                        is_admin=True,
                    )
                }
            ),
        ),
        imprint=request.param[0],
    )

    with open(CONFIG_PATH, "w") as f:
        json.dump(settings.model_dump(), f)

    subprocess.run(["docker" "compose" "restart" "project-w"], check=True)
    wait_for_backend()

    yield (f"{BACKEND_BASE_URL}/api/", smtpd)

    with psycopg.connect(str(postgres_connection)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DROP SCHEMA project_w CASCADE
            """
            )

    r = redis.Redis()
    redis_client = r.from_url(str(redis_connection))
    redis_client.flushdb()
