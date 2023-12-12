
from werkzeug import Client


def test_submitJob_invalid(client: Client, user):
    # missing auth header
    res = client.post("/api/jobs/submit")
    assert 400 <= res.status_code < 500

    # missing form data
    res = client.post("/api/jobs/submit", headers=user)
    assert 400 <= res.status_code < 500


def test_submitJob_valid(client: Client, user, audio):
    res = client.post("/api/jobs/submit", headers=user, data={"file": audio})
    assert res.status_code == 200
    assert "job_id" in res.json


def test_listJobs_invalid(client: Client, user, admin):
    # missing auth header
    res = client.get("/api/jobs/list")
    assert 400 <= res.status_code < 500

    # unauthorized accesses
    res = client.get("/api/jobs/list", headers=user, query_string={"all": True})
    assert res.status_code == 403
    assert res.json["message"] == "You don't have permission to list other users' jobs"

    res = client.get("/api/jobs/list", headers=user, query_string={"email": "admin@test.com"})
    assert res.status_code == 403
    assert res.json["message"] == "You don't have permission to list other users' jobs"

    # nonexistent user
    res = client.get("/api/jobs/list", headers=admin, query_string={"email": "fake@test.com"})
    assert res.status_code == 400


def test_listJobs_valid(client: Client, user, admin):
    res = client.get("/api/jobs/list", headers=user)
    assert res.status_code == 200
    assert len(res.json["job_ids"]) == 1

    res = client.get("/api/jobs/list", headers=admin, query_string={"email": "user@test.com"})
    assert res.status_code == 200
    assert len(res.json["job_ids"]) == 1

    res = client.get("/api/jobs/list", headers=admin, query_string={"all": True})
    assert res.status_code == 200
    assert len(res.json) == 2


def test_jobStatus_invalid(client: Client, user, admin):
    # missing credentials
    res = client.get("/api/jobs/status")
    assert 400 <= res.status_code < 500

    # invalid job id/no permission
    # 1 is a job by a different user, 3 doesn't exist
    for job_id in [1, 3]:
        res = client.get("/api/jobs/status", headers=user,
                         query_string={"job_id": job_id})
        assert res.status_code == 403
        assert res.json["message"] == "You don't have permission to access this job"
    
    # invalid job id but as admin
    res = client.get("/api/jobs/status", headers=admin, query_string={"job_id": 3})
    assert res.status_code == 404
    assert res.json["message"] == "There exists no job with that id"

def test_jobStatus_valid(client: Client, user, admin):
    # users can lookup their own jobs
    res = client.get("/api/jobs/status", headers=user, query_string={"job_id": 2})
    assert res.status_code == 200
    assert "status" in res.json

    # admins can lookup other users' jobs
    res = client.get("/api/jobs/status", headers=admin, query_string={"job_id": 2})
    assert res.status_code == 200
    assert "status" in res.json