
import pytest
from werkzeug import Client


@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_submitJob_invalid(client: Client, user):
    # missing auth header
    res = client.post("/api/jobs/submit")
    assert 400 <= res.status_code < 500

    # missing form data
    res = client.post("/api/jobs/submit", headers=user)
    assert 400 <= res.status_code < 500


@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_submitJob_valid(client: Client, user, audio):
    res = client.post("/api/jobs/submit", headers=user, data={"file": audio})
    assert res.status_code == 200
    assert "jobId" in res.json


@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_listJobs_invalid(client: Client, user, admin):
    # missing auth header
    res = client.get("/api/jobs/list")
    assert 400 <= res.status_code < 500

    # unauthorized accesses
    res = client.get("/api/jobs/list", headers=user,
                     query_string={"all": True})
    assert res.status_code == 403
    assert res.json["msg"] == "You don't have permission to list other users' jobs"

    res = client.get("/api/jobs/list", headers=user,
                     query_string={"email": "admin@test.com"})
    assert res.status_code == 403
    assert res.json["msg"] == "You don't have permission to list other users' jobs"

    # nonexistent user
    res = client.get("/api/jobs/list", headers=admin,
                     query_string={"email": "fake@test.com"})
    assert res.status_code == 400


@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_listJobs_valid(client: Client, user, admin):
    res = client.get("/api/jobs/list", headers=user)
    assert res.status_code == 200
    assert len(res.json["jobIds"]) == 1

    res = client.get("/api/jobs/list", headers=admin,
                     query_string={"email": "user@test.com"})
    assert res.status_code == 200
    assert len(res.json["jobIds"]) == 1

    res = client.get("/api/jobs/list", headers=admin,
                     query_string={"all": True})
    assert res.status_code == 200
    assert len(res.json) == 2


@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_jobInfo_invalid(client: Client, user, admin):
    # missing credentials
    res = client.post("/api/jobs/info")
    assert 400 <= res.status_code < 500

    # invalid job id/no permission
    # 1 is a job by a different user, 3 doesn't exist
    for job_id in [1, 3]:
        res = client.post("/api/jobs/info", headers=user,
                          data={"jobIds": job_id})
        assert res.status_code == 403
        assert res.json[
            "msg"] == f"You don't have permission to access the job with id {job_id}"

    # invalid job id but as admin
    res = client.post("/api/jobs/info", headers=admin, data={"jobIds": 3})
    assert res.status_code == 404
    assert res.json["msg"] == "There exists no job with id 3"


@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_jobInfo_valid(client: Client, user, admin):
    # users can lookup their own jobs
    res = client.post("/api/jobs/info", headers=user, data={"jobIds": 2})
    assert res.status_code == 200
    assert len(res.json) == 1
    assert "jobId" in res.json[0]
    assert "fileName" in res.json[0]
    assert "model" in res.json[0]
    assert "language" in res.json[0]
    assert "status" in res.json[0]

    # admins can lookup other users' jobs
    res = client.post("/api/jobs/info", headers=admin, data={"jobIds": 2})
    assert res.status_code == 200
    assert len(res.json) == 1
    assert "jobId" in res.json[0]
    assert "fileName" in res.json[0]
    assert "model" in res.json[0]
    assert "language" in res.json[0]
    assert "status" in res.json[0]

    res = client.post("/api/jobs/info", headers=admin, data={"jobIds": "1,2"})
    assert res.status_code == 200
    assert len(res.json) == 2
