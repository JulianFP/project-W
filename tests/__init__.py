
from typing import Dict

def get_auth_headers(
    client, email: str = "user@test.com", password: str = "user"
) -> Dict[str, str]:
    response = client.post(
        "/api/login", data={"email": email, "password": password})
    token = response.json["accessToken"]
    return {"Authorization": f"Bearer {token}"}
