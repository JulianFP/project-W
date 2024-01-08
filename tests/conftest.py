import os
import sys
import pytest
from project_W import create_app
from tests import get_auth_headers

sys.path.append(os.path.join(os.path.dirname(__file__), "helpers"))

import flask_test_utils as ftu

#client fixture requires the following param: (str, str)
#the strings will be the config values of 'allowedEmailDomains' and 'disableSignup' respectively and thus have to be written in yaml syntax
@pytest.fixture(scope="function")
def client(request, tmp_path):
    #patch config.yml file
    temp_config_path = str(tmp_path / "config.yml")
    temp_db_dir = str(tmp_path)
    configFile = open(temp_config_path, "w")
    configFile.write(
    f"url: 'https://example.com'\n"
    f"databasePath: '{temp_db_dir}'\n"
    f"loginSecurity:\n"
    f"    sessionSecretKey: 'abcdefghijklmnopqrstuvwxyz'\n"
    f"    allowedEmailDomains: {request.param[0]}\n" 
    f"    disableSignup: {request.param[1]}\n"
    f"smtpServer:\n"
    f"    domain: 'smtp.example.com'\n"
    f"    port: 587\n"
    f"    secure: 'unencrypted'\n"
    f"    senderEmail: 'alice@example.com'\n"
    f"    username: 'alice@example.com'\n"
    f"    password: 'thisisabadpassword'")
    configFile.close()

    app = create_app(configFile.name)
    ftu.add_test_users(app)

    yield app.test_client()

@pytest.fixture()
def mockedSMTP(mocker):
    mock_SMTP = mocker.MagicMock(name="project_W.model.SMTP")
    mocker.patch("project_W.model.SMTP", new=mock_SMTP)

    yield mock_SMTP

def _auth_fixture(email, password):
    @pytest.fixture()
    def auth(client):
        return get_auth_headers(client, email, password)
    return auth

user = _auth_fixture("user@test.com", "userPassword1!")
admin = _auth_fixture("admin@test.com", "adminPassword1!")
