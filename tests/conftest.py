import json
import os
import secrets
import subprocess
import sys
import time

import httpx
import psycopg
import pytest
import redis

BACKEND_BASE_URL = "https://localhost:8443"


@pytest.fixture(scope="session")
def secret_key():
    return secrets.token_hex(32)


def wait_for_backend(timeout=30):
    for _ in range(timeout):
        try:
            httpx.get(f"{BACKEND_BASE_URL}/api/about", verify=False).raise_for_status()
            return
        except httpx.HTTPError:
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

    with open("./backend-config/config.yml", "w") as f:
        json.dump(settings, f)

    subprocess.run(
        [
            "docker",
            "run",
            "--name",
            "Project-W",
            "--rm",
            "--network",
            "host",
            "-v",
            "./backend-config:/etc/xdg/project-W/",
            "-d",
            "project-w",
        ],
        check=True,
    )
    with subprocess.Popen(
        ["docker", "logs", "-f", "Project-W"],
        stdout=sys.stdout,
        stderr=sys.stderr,
    ) as process:
        wait_for_backend()

        yield (f"{BACKEND_BASE_URL}/api/", smtpd)

        process.terminate()

    subprocess.run(
        [
            "docker",
            "stop",
            "Project-W",
        ],
        check=True,
    )

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


@pytest.fixture(scope="function")
def runner():

    created_runners = []

    def _runner_factory(name: str, priority: int):
        wait_for_backend()
        response = httpx.post(f"{BACKEND_BASE_URL}/api/admins/create_runner")
        content = response.json()

        settings = {
            "backend_url": BACKEND_BASE_URL,
            "runner_name": name,
            "runner_priority": priority,
            "runner_token": content["token"],
            "whisper_settings": {
                "model_cache_dir": "/models",
                "hf_token": "",
                "torch_device": "cpu",
                "compute_type": "int8",
                "batch_size": 4,
            },
        }

        runner_config_path = f"runner-{name}-config/config.yml"

        os.makedirs(os.path.dirname(runner_config_path), exist_ok=True)
        with open(runner_config_path, "w") as f:
            json.dump(settings, f)

        container_name = f"runner-{name}"
        created_runners.append(container_name)
        os.makedirs("./runner-models", exist_ok=True)
        subprocess.run(
            [
                "docker",
                "run",
                "--name",
                container_name,
                "--rm",
                "--network",
                "host",
                "-v",
                f"./runner-{name}-config:/etc/xdg/project-W-runner/",
                "-v",
                "./runner-models:/models/",
                "-d",
                "project-w_runner",
            ],
            check=True,
        )

        return content["id"]

    yield _runner_factory

    for container_name in created_runners:
        subprocess.run(
            [
                "docker",
                "stop",
                container_name,
            ],
            check=True,
        )
