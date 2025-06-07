import pytest
import requests


@pytest.mark.parametrize(
    "backend",
    [
        (
            {
                "name": "CI",
                "email": "ci@example.org",
                "additional_imprint_html": "<div>hello</div>",
            },
        ),
        (None,),
    ],
    indirect=True,
)
def test_about(backend):
    (base_url, _) = backend

    response = requests.get(f"{base_url}about", verify=False)
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"
    content = response.json()
    assert (
        content.get("description")
        == "A self-hostable platform on which users can create transcripts of their audio files (speech-to-text) using Whisper AI"
    )
    assert content.get("source_code") == "https://github.com/JulianFP/project-W"
    assert type(content.get("version")) == str


@pytest.mark.parametrize(
    "backend",
    [
        (
            {
                "name": "CI",
                "email": "ci@example.org",
                "additional_imprint_html": "<div>hello</div>",
            },
        ),
    ],
    indirect=True,
)
def test_about_imprint(backend):
    (base_url, _) = backend

    response = requests.get(f"{base_url}about", verify=False)
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"
    content = response.json()
    assert content.get("imprint").get("name") == "CI"
    assert content.get("email").get("name") == "ci@example.org"
    assert content.get("email").get("additional_imprint_html") == "<div>hello</div>"
