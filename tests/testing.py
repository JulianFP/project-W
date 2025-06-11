import os
from io import BytesIO

import httpx

dummy_file = BytesIO(os.urandom(900))  # generate 1KiB random binary file

files = {"audio_file": ("dummy-file", dummy_file, "audio/aac")}
headers = {
    "Authorization": f"Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX3R5cGUiOiJsb2NhbCIsInN1YiI6IjEiLCJlbWFpbCI6ImFkbWluQHBhcnRhbmVuZ3JvdXAuZGUiLCJpc192ZXJpZmllZCI6dHJ1ZSwic2NvcGVzIjpbXSwidG9rZW5faWQiOjEsImlzcyI6InByb2plY3QtVyIsImV4cCI6MTc0OTYxMzQxMX0.2YD52fwu__VveMgKyQVmQpNqov3LBgBrwMHkFxQ2tJs"
}
response = httpx.post("http://localhost:8000/api/jobs/submit_job", files=files, headers=headers)
assert response.status_code == httpx.codes.OK
job_id = response.json()
