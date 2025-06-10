import json
import os
import re
import secrets
import shutil
import ssl
import subprocess
import sys
import time

import httpx
import psycopg
import pytest
import redis


class HelperFunctions:
    def wait_for_backend(self, base_url: str, timeout: int = 30):
        for _ in range(timeout):
            try:
                httpx.get(f"{base_url}/api/about", verify=False).raise_for_status()
                return
            except httpx.HTTPError:
                time.sleep(1)
        raise TimeoutError("Server did not become healthy in time.")

    def wait_for_job_assignment(self, job_id: int, client: httpx.Client, timeout: int = 30):
        for _ in range(timeout):
            response = client.get(f"/api/jobs/info?job_ids={job_id}")
            response.raise_for_status()
            job_info = response.json()
            if job_info[0].get("runner_id"):
                return
            time.sleep(1)
        raise TimeoutError("Runner was not assigned to the job in time.")

    def wait_for_job_completion(self, job_id: int, client: httpx.Client, timeout: int = 30):
        for _ in range(timeout):
            response = client.get(f"/api/jobs/info?job_ids={job_id}")
            response.raise_for_status()
            job_info = response.json()
            if job_info[0].get("step") == "success":
                return
            time.sleep(1)
        raise TimeoutError("Job was not completed in time.")


@pytest.fixture(scope="session")
def helper_functions():
    return HelperFunctions()


@pytest.fixture(scope="session")
def secret_key():
    return secrets.token_hex(32)


@pytest.fixture(scope="function")
def backend(request, smtpd, secret_key, helper_functions):
    BACKEND_BASE_URL = "https://localhost:8443"

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
                    },
                    1: {
                        "email": "user@example.org",
                        "password": "Password-1234",
                        "is_admin": False,
                    },
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
        helper_functions.wait_for_backend(BACKEND_BASE_URL)

        yield (f"{BACKEND_BASE_URL}", smtpd)

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
def get_client(backend):
    clients = []

    def _client_factory(headers: dict[str, str] = {}):
        cafile = "./backend-config/certs/cert.pem"
        ctx = ssl.create_default_context(cafile=cafile)
        client = httpx.Client(base_url=backend[0], headers=headers, verify=ctx)
        clients.append(client)
        return client

    yield _client_factory

    for client in clients:
        client.close()


@pytest.fixture(scope="function")
def get_logged_in_client(get_client):
    def _client_factory(as_admin: bool = False):
        password = "Password-1234"
        if as_admin:
            email = "admin@example.org"
        else:
            email = "user@example.org"

        client = get_client()
        response = client.post(
            "/api/local-account/login",
            data={
                "grant_type": "password",
                "username": email,
                "password": password,
                "scope": "admin" if as_admin else "",
            },
        )
        response.raise_for_status()
        headers = {"Authorization": f"Bearer {response.json()}"}
        return get_client(headers)

    return _client_factory


@pytest.fixture(scope="function")
def get_runner(backend, get_logged_in_client):

    created_runners = []

    def _runner_factory(name: str, priority: int):
        client = get_logged_in_client(as_admin=True)
        response = client.post("/api/admins/create_runner")
        response.raise_for_status()
        content = response.json()

        settings = {
            "runner_attributes": {
                "name": name,
                "priority": priority,
            },
            "backend_settings": {
                "url": backend[0],
                "auth_token": content["token"],
                "ca_pem_file_path": "/etc/xdg/project-W-runner/backend-cert.pem",
            },
            "whisper_settings": {
                "hf_token": "abcd",
            },
        }

        runner_config_dir = f"runner-{name}-config"
        os.makedirs(runner_config_dir, exist_ok=True)
        shutil.copyfile("./backend-config/certs/cert.pem", f"{runner_config_dir}/backend-cert.pem")
        with open(f"{runner_config_dir}/config.yml", "w") as f:
            json.dump(settings, f)

        normalized_name = re.sub("[^a-zA-Z0-9_.-]", "_", name)
        container_name = f"runner-{normalized_name}"
        created_runners.append(container_name)
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
                "-d",
                "project-w_runner_dummy",
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
