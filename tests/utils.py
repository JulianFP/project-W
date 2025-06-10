import time

import httpx


def wait_for_backend(base_url: str, timeout: int = 30):
    for _ in range(timeout):
        try:
            httpx.get(f"{base_url}/api/about", verify=False).raise_for_status()
            return
        except httpx.HTTPError:
            time.sleep(1)
    raise TimeoutError("Server did not become healthy in time.")


def wait_for_job_assignment(job_id: int, client: httpx.Client, timeout: int = 30):
    for _ in range(timeout):
        response = client.get(f"/api/jobs/info?job_ids={job_id}")
        response.raise_for_status()
        job_info = response.json()
        if job_info.get("runner_id"):
            return
        time.sleep(1)
    raise TimeoutError("Runner was not assigned to the job in time.")


def wait_for_job_completion(job_id: int, client: httpx.Client, timeout: int = 30):
    for _ in range(timeout):
        response = client.get(f"/api/jobs/info?job_ids={job_id}")
        response.raise_for_status()
        job_info = response.json()
        if job_info.get("step") == "success":
            return
        time.sleep(1)
    raise TimeoutError("Job was not completed in time.")
