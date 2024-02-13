import pytest, smtplib
from werkzeug import Client
from tests import get_auth_headers

#disableSignup has been set in config.yml
@pytest.mark.parametrize("client", [("[]", "true"), ("[ 'test.com' ]", "true"), ("[ 'test.com', 'sub.test.com' ]", "true")], indirect=True)
def test_signup_invalid_disabledSignup(client: Client):
    res = client.post(
        "/api/signup", data={"email": "user2@test.com", "password": "user2Password1!"})
    assert res.status_code == 400
    assert res.json["msg"] == "Signup of new accounts is disabled on this server"
    assert res.json["errorType"] == "serverConfig"

# missing form data
@pytest.mark.parametrize("client", [("[]", "false"), ("[ 'test.com' ]", "false"), ("[ 'test.com', 'sub.test.com' ]", "false")], indirect=True)
def test_signup_invalid_missingFormData(client: Client):
    res = client.post("/api/signup")
    # leads to a flask error
    assert 400 <= res.status_code < 500

# provided 'email' is not an email address
@pytest.mark.parametrize("client, email", [(("[]", "false"), "abcdefg"), (("[]", "false"), "user2"), (("[]", "false"), "user2@test"), (("[]", "false"), "user2@test."), (("[]", "false"), "@test.com")], indirect=["client"])
def test_signup_invalid_invalidEmail1(client: Client, email: str):
    res = client.post(
        "/api/signup", data={"email": email, "password": "user2Password1!"})
    assert res.status_code == 400
    assert res.json["msg"] == f"'{email}' is not a valid email address"
    assert res.json["allowedEmailDomains"] == []
    assert res.json["errorType"] == "email"

# provided 'email's domain is not in 'allowedEmailDomains'
@pytest.mark.parametrize("client, email", [(("[ 'test.com' ]", "false"), "user2@test.de"), (("[ 'test.com' ]", "false"), "user2@sub.test.com")], indirect=["client"])
def test_signup_invalid_invalidEmail2(client: Client, email: str):
    res = client.post(
        "/api/signup", data={"email": email, "password": "user2Password1!"})
    assert res.status_code == 400
    assert res.json["msg"] == f"'{email}' is not a valid email address"
    assert res.json["allowedEmailDomains"] == [ 'test.com' ]
    assert res.json["errorType"] == "email"

# provided 'password' does not fit criteria
@pytest.mark.parametrize("client, password", [(("[]", "false"), "user2"), (("[]", "false"), "tooShort58!"), (("[]", "false"), "thispasswordhasnouppercasechars390!"), (("[]", "false"), "THISPASSWORDHASNOLOWERCASE$%=56"), (("[]", "false"), "ThisPasswordHasNoNumbers!"), (("[]", "false"), "ThisPasswordHasNoSymbols123"), (("[]", "false"), "thispasswordhasnouppercasechars390!")], indirect=["client"])
def test_signup_invalid_invalidPassword(client: Client, password: str):
    res = client.post(
        "/api/signup", data={"email": "user2@test.com", "password": password})
    assert res.status_code == 400
    assert res.json["msg"] == "Password invalid. The password needs to have at least one lowercase letter, uppercase letter, number, special character and at least 12 characters in total"
    assert res.json["errorType"] == "password"

# user email is already in use
@pytest.mark.parametrize("client", [("[]", "false"), ("[ 'test.com' ]", "false"), ("[ 'test.com', 'sub.test.com' ]", "false")], indirect=True)
def test_signup_invalid_emailAlreadyInUse(client: Client):
    res = client.post(
        "/api/signup", data={"email": "user@test.com", "password": "user2Password1!"})
    assert res.status_code == 400
    assert res.json["msg"] == "E-Mail is already used by another account"
    assert res.json["errorType"] == "email"

# email couldn't be sent
@pytest.mark.parametrize("client", [("[]", "false"), ("[ 'test.com' ]", "false"), ("[ 'test.com', 'sub.test.com' ]", "false")], indirect=True)
def test_signup_invalid_brokenSMTP(client: Client, mockedSMTP):
    mockedSMTP.side_effect = smtplib.SMTPException

    res = client.post(
        "/api/signup", data={"email": "user2@test.com", "password": "user2Password1!"})
    assert res.status_code == 400
    assert res.json["msg"] == "Failed to send activation email to user2@test.com. Email address may not exist"
    assert res.json["errorType"] == "email"

    #smtp stuff
    assert mockedSMTP.call_count == 1


@pytest.mark.parametrize("client", [("[]", "false"), ("[ 'test.com' ]", "false"), ("[ 'test.com', 'sub.test.com' ]", "false")], indirect=True)
def test_signup_valid(client: Client, mockedSMTP):
    res = client.post(
        "/api/signup", data={"email": "user2@test.com", "password": "user2Password1!"})
    assert res.status_code == 200
    assert res.json["msg"] == "Successful signup for user2@test.com. Please activate your account be clicking on the link provided in the email we just sent you"

    #smtp stuff
    assert mockedSMTP.call_count == 1
    msg = mockedSMTP.mock_calls[3][1][0]
    assert msg["Subject"] == "Project-W account activation"
    assert msg["From"] == "alice@example.com"
    assert msg["To"] == "user2@test.com"
    body = msg.get_content()
    assert body.startswith("To activate your Project-W account")
    assert body.count("https://example.com/activate?token=")
    



#no token in query string
@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_activate_invalid_noToken(client: Client):
    res = client.get("/api/activate")
    assert res.status_code == 400
    assert res.json["msg"] == "You need a token to activate a users email"
    assert res.json["errorType"] == "auth"

#invalid token in query string
@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_activate_invalid_invalidToken(client: Client):
    #hint: tokens are 127 characters long
    res = client.get("/api/activate", query_string={"token": "safjdDkdf8239hf839fdFsdfas.FDSf239dHF001fdhFDFfuisagu.6asdjgKOPFDdfsFDDgufg898989898dU89789fFDDGudufFD123449FGDjhgdfhgfua5438FD"})
    assert res.status_code == 400
    assert res.json["msg"] == "Invalid or expired activation link"
    assert res.json["errorType"] == "auth"

#user deleted before activation
@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_activate_invalid_userDeleted(client: Client, mockedSMTP):
    res = client.post(
        "/api/signup", data={"email": "user2@test.com", "password": "user2Password1!"})
    assert res.status_code == 200

    msgBody = mockedSMTP.mock_calls[3][1][0].get_content()
    tokenLine = msgBody.split('\n')[2]
    token = tokenLine.partition("token=")[2]

    user2 = get_auth_headers(client, "user2@test.com", "user2Password1!")
    res = client.post("/api/deleteUser", headers=user2,
                      data={"password": "user2Password1!"})
    assert res.status_code == 200

    res = client.get("/api/activate", query_string={"token": token})
    assert res.status_code == 400
    assert res.json["msg"] == "No user with email user2@test.com exists"
    assert res.json["errorType"] == "notInDatabase"

#user already activated
@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_activate_invalid_userAlreadyActivated(client: Client, mockedSMTP):
    res = client.post(
        "/api/signup", data={"email": "user2@test.com", "password": "user2Password1!"})

    msgBody = mockedSMTP.mock_calls[3][1][0].get_content()
    tokenLine = msgBody.split('\n')[2]
    token = tokenLine.partition("token=")[2]

    res = client.get("/api/activate", query_string={"token": token})
    assert res.status_code == 200

    res = client.get("/api/activate", query_string={"token": token})
    assert res.status_code == 400
    assert res.json["msg"] == "Account for user2@test.com is already activated"
    assert res.json["errorType"] == "operation"


#valid after accout signup
@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_activate_valid_signup(client: Client, mockedSMTP):
    res = client.post(
        "/api/signup", data={"email": "user2@test.com", "password": "user2Password1!"})
    assert res.status_code == 200

    msgBody = mockedSMTP.mock_calls[3][1][0].get_content()
    tokenLine = msgBody.split('\n')[2]
    token = tokenLine.partition("token=")[2]

    res = client.get("/api/activate", query_string={"token": token})
    assert res.status_code == 200
    assert res.json["msg"] == "Account user2@test.com activated"

#valid after email address change
@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_activate_valid_emailChange(client: Client, mockedSMTP, user):
    res = client.post("/api/changeUserEmail", headers=user,
                      data={"password": "userPassword1!", "newEmail": "user2@test.com"})
    assert res.status_code == 200

    msgBody = mockedSMTP.mock_calls[3][1][0].get_content()
    tokenLine = msgBody.split('\n')[2]
    token = tokenLine.partition("token=")[2]

    res = client.get("/api/activate", query_string={"token": token})
    assert res.status_code == 200
    assert res.json["msg"] == "Account user2@test.com activated"

#JWT Token still valid after account activation
@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_activate_valid_tokenStaysValid(client: Client, mockedSMTP):
    email: str = "user2@test.com"
    password: str = "user2Password1!"
    signupRes = client.post(
        "/api/signup", data={"email": email, "password": password})
    assert signupRes.status_code == 200

    user2 = get_auth_headers(client, email, password)

    msgBody = mockedSMTP.mock_calls[3][1][0].get_content()
    tokenLine = msgBody.split('\n')[2]
    token = tokenLine.partition("token=")[2]
    activateRes = client.get("/api/activate", query_string={"token": token})
    assert activateRes.status_code == 200

    userinfoRes = client.get("/api/userinfo", headers=user2)
    assert userinfoRes.status_code == 200




# missing form data
@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_login_invalid_missingFormData(client: Client):
    res = client.post("/api/login")
    assert 400 <= res.status_code < 500

# unknown email
@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_login_invalid_unknownEmail(client: Client):
    res = client.post("/api/login", data={"email": "", "password": "user2Password1!"})
    assert res.status_code == 400
    assert res.json["msg"] == "Incorrect credentials provided"
    assert res.json["errorType"] == "auth"

# wrong password
@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_login_invalid_wrongPassword(client: Client):
    res = client.post(
        "/api/login", data={"email": "user@test.com", "password": "user2Password1!"})
    assert res.status_code == 400
    assert res.json["msg"] == "Incorrect credentials provided"
    assert res.json["errorType"] == "auth"


@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_login_valid(client: Client):
    email = "user@test.com"
    password = "userPassword1!"
    response = client.post(
        "/api/login", data={"email": email, "password": password})
    assert response.status_code == 200
    assert response.json["msg"] == "Login successful"
    assert "access_token" in response.json




# provided 'email' doesn't belong to any user
@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_requestPasswordReset_invalid_invalidEmail(client: Client, mockedSMTP):
    res = client.post(
        "/api/requestPasswordReset", data={"email": "user2@test.com", "password": "user2Password1!"})
    #you shouldn't be able to see from the client side if an entered email belongs to a user or not
    assert res.status_code == 200
    assert res.json["msg"] == f"If an account with the address user2@test.com exists, then we sent a password reset email to this address. Please check your emails"

    #However we can test this by making sure that no email got sent:
    assert mockedSMTP.call_count == 0

# email couldn't be sent
@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_requestPasswordReset_invalid_brokenSMTP(client: Client, mockedSMTP):
    mockedSMTP.side_effect = smtplib.SMTPException

    res = client.post(
        "/api/requestPasswordReset", data={"email": "user@test.com", "password": "userPassword1!"})
    assert res.status_code == 400
    assert res.json["msg"] == "Failed to send password reset email to user@test.com."
    assert res.json["errorType"] == "email"

    #smtp stuff
    assert mockedSMTP.call_count == 1

@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_requestPasswordReset_valid(client: Client, mockedSMTP):
    res = client.post(
        "/api/requestPasswordReset", data={"email": "user@test.com", "password": "userPassword1!"})
    assert res.status_code == 200
    assert res.json["msg"] == f"If an account with the address user@test.com exists, then we sent a password reset email to this address. Please check your emails"

    #smtp stuff 
    assert mockedSMTP.call_count == 1
    msg = mockedSMTP.mock_calls[3][1][0]
    assert msg["Subject"] == "Project-W password reset request"
    assert msg["From"] == "alice@example.com"
    assert msg["To"] == "user@test.com"
    body = msg.get_content()
    assert body.startswith("To reset the password of your Project-W account")
    assert body.count("https://example.com/resetPassword?token=")




#no token in query string
@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_resetPassword_invalid_noToken(client: Client):
    res = client.post(
        "/api/resetPassword", data={"newPassword": "user2Password1!"})
    assert res.status_code == 400
    assert res.json["msg"] == "You need a token to reset a users password"
    assert res.json["errorType"] == "auth"

#invalid token in query string
@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_resetPassword_invalid_invalidToken(client: Client):
    #hint: tokens are 127 characters long
    res = client.post(
        "/api/resetPassword", query_string={"token": "safjdDkdf8239hf839fdFsdfas.FDSf239dHF001fdhFDFfuisagu.6asdjgKOPFDdfsFDDgufg898989898dU89789fFDDGudufFD123449FGDjhgdfhgfua5438FD"}, data={"newPassword": "user2Password1!"})
    assert res.status_code == 400
    assert res.json["msg"] == "Invalid or expired password reset link"
    assert res.json["errorType"] == "auth"

# provided 'password' does not fit criteria
@pytest.mark.parametrize("client, password", [(("[]", "false"), "user2"), (("[]", "false"), "tooShort58!"), (("[]", "false"), "thispasswordhasnouppercasechars390!"), (("[]", "false"), "THISPASSWORDHASNOLOWERCASE$%=56"), (("[]", "false"), "ThisPasswordHasNoNumbers!"), (("[]", "false"), "ThisPasswordHasNoSymbols123"), (("[]", "false"), "thispasswordhasnouppercasechars390!")], indirect=["client"])
def test_resetPassword_invalid_invalidPassword(client: Client, mockedSMTP, password: str):
    res = client.post(
        "/api/requestPasswordReset", data={"email": "user@test.com", "password": "userPassword1!"})
    assert res.status_code == 200

    msgBody = mockedSMTP.mock_calls[3][1][0].get_content()
    tokenLine = msgBody.split('\n')[2]
    token = tokenLine.partition("token=")[2]

    res = client.post(
        "/api/resetPassword", query_string={"token": token}, data={"newPassword": password})
    assert res.status_code == 400
    assert res.json["msg"] == "Password invalid. The password needs to have at least one lowercase letter, uppercase letter, number, special character and at least 12 characters in total"
    assert res.json["errorType"] == "password"

#user deleted before password reset
@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_resetPassword_invalid_userDeleted(client: Client, mockedSMTP, user):
    res = client.post(
        "/api/requestPasswordReset", data={"email": "user@test.com", "password": "userPassword1!"})
    assert res.status_code == 200

    msgBody = mockedSMTP.mock_calls[3][1][0].get_content()
    tokenLine = msgBody.split('\n')[2]
    token = tokenLine.partition("token=")[2]

    res = client.post("/api/deleteUser", headers=user,
                      data={"password": "userPassword1!"})
    assert res.status_code == 200

    res = client.post(
        "/api/resetPassword", query_string={"token": token}, data={"newPassword": "user2Password1!"})
    assert res.status_code == 400
    assert res.json["msg"] == "Unknown email address user@test.com"
    assert res.json["errorType"] == "notInDatabase"

@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_resetPassword_valid(client: Client, mockedSMTP):
    res = client.post(
        "/api/requestPasswordReset", data={"email": "user@test.com", "password": "userPassword1!"})
    assert res.status_code == 200

    msgBody = mockedSMTP.mock_calls[3][1][0].get_content()
    tokenLine = msgBody.split('\n')[2]
    token = tokenLine.partition("token=")[2]

    res = client.post(
        "/api/resetPassword", query_string={"token": token}, data={"newPassword": "user2Password1!"})
    assert res.status_code == 200
    assert res.json["msg"] == "password changed successfully"

    assert mockedSMTP.call_count == 1


# non-admins can't access other users' infos
@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_userinfo_invalid_noPermissions(client: Client, user):
    res = client.get("/api/userinfo", headers=user,
                     query_string={"email": "admin@test.com"})
    assert res.status_code == 403
    assert res.json["msg"] == "You don't have permission to view other accounts' user info"
    assert res.json["errorType"] == "permission"

# can't access non-existent user info
@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_userinfo_invalid_wrongEmail(client: Client, admin):
    res = client.get("/api/userinfo", headers=admin,
                     query_string={"email": "fake@test.com"})
    assert res.status_code == 400
    assert res.json["msg"] == "No user exists with that email"
    assert res.json["errorType"] == "notInDatabase"


# non-admins can access their own user info
@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_userinfo_valid_nonAdmins(client: Client, user):
    res = client.get("/api/userinfo", headers=user)
    assert res.status_code == 200
    assert res.json["email"] == "user@test.com"
    assert res.json["is_admin"] == False

@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_userinfo_valid_admins(client: Client, admin):
    # admins can also access their own user info
    res = client.get("/api/userinfo", headers=admin)
    assert res.status_code == 200
    assert res.json["email"] == "admin@test.com"
    assert res.json["is_admin"] == True

    # admins can access other users' info
    res = client.get("/api/userinfo", headers=admin,
                     query_string={"email": "user@test.com"})
    assert res.status_code == 200
    assert res.json["email"] == "user@test.com"
    assert res.json["is_admin"] == False




# wrong password
@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_deleteUser_invalid_wrongPassword(client: Client, user):
    res = client.post("/api/deleteUser", headers=user,
                      data={"password": "user2Password1!"})
    assert res.status_code == 403
    assert res.json["msg"] == "Incorrect password provided"
    assert res.json["errorType"] == "auth"

# normal user who tries to delete other user
@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_deleteUser_invalid_noPermissions(client: Client, user):
    res = client.post("/api/deleteUser", headers=user,
                      data={"password": "userPassword1!", "emailModify": "admin@test.com"})
    assert res.status_code == 403
    assert res.json["msg"] == "You don't have permission to modify other users"
    assert res.json["errorType"] == "permission"

# admin user who tries to delete other user, but email is invalid
@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_deleteUser_invalid_wrongEmail(client: Client, admin):
    res = client.post("/api/deleteUser", headers=admin,
                      data={"password": "adminPassword1!", "emailModify": "abc@xyz.com"})
    assert res.status_code == 400
    assert res.json["msg"] == "No user exists with that email"
    assert res.json["errorType"] == "notInDatabase"


# normal user deletes themselves
@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_deleteUser_valid_nonAdmins(client: Client, user):
    res = client.post("/api/deleteUser", headers=user,
                      data={"password": "userPassword1!"})
    assert res.status_code == 200
    assert res.json["msg"] == "Successfully deleted user with email user@test.com"

# admin user deletes other user
@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_deleteUser_valid_Admins(client: Client, admin):
    res = client.post("/api/deleteUser", headers=admin,
                      data={"password": "adminPassword1!", "emailModify": "user@test.com"})
    assert res.status_code == 200
    assert res.json["msg"] == "Successfully deleted user with email user@test.com"




# wrong password
@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_changeUserPassword_invalid_wrongPassword(client: Client, user):
    res = client.post("/api/changeUserPassword", headers=user,
                      data={"password": "userPassword2!", "newPassword": "user2Password1!"})
    assert res.status_code == 403
    assert res.json["msg"] == "Incorrect password provided"
    assert res.json["errorType"] == "auth"

# normal user who tries to modify other user
@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_changeUserPassword_invalid_noPermissions(client: Client, user):
    res = client.post("/api/changeUserPassword", headers=user, data={
                      "password": "userPassword1!", "newPassword": "user2Password1!", "emailModify": "admin@test.com"})
    assert res.status_code == 403
    assert res.json["msg"] == "You don't have permission to modify other users"
    assert res.json["errorType"] == "permission"

# admin user who tries to modify other user, but email is invalid
@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_changeUserPassword_invalid_wrongEmail(client: Client, admin):
    res = client.post("/api/changeUserPassword", headers=admin, data={
                      "password": "adminPassword1!", "newPassword": "adminPassword2!", "emailModify": "abc@xyz.com"})
    assert res.status_code == 400
    assert res.json["msg"] == "No user exists with that email"
    assert res.json["errorType"] == "notInDatabase"

#newPassword does not meet criteria
@pytest.mark.parametrize("client, password", [(("[]", "false"), "user2"), (("[]", "false"), "tooShort58!"), (("[]", "false"), "thispasswordhasnouppercasechars390!"), (("[]", "false"), "THISPASSWORDHASNOLOWERCASE$%=56"), (("[]", "false"), "ThisPasswordHasNoNumbers!"), (("[]", "false"), "ThisPasswordHasNoSymbols123"), (("[]", "false"), "thispasswordhasnouppercasechars390!")], indirect=["client"])
def test_changeUserPassword_invalid_invalidPassword(client: Client, password: str, user):
    res = client.post("/api/changeUserPassword", headers=user,
                      data={"password": "userPassword1!", "newPassword": password})
    assert res.status_code == 400
    assert res.json["msg"] == "Password invalid. The password needs to have at least one lowercase letter, uppercase letter, number, special character and at least 12 characters in total"
    assert res.json["errorType"] == "password"


# normal user modifies themselves
@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_changeUserPassword_valid_normal(client: Client, user):
    res = client.post("/api/changeUserPassword", headers=user,
                      data={"password": "userPassword1!", "newPassword": "user2Password1!"})
    assert res.status_code == 200
    assert res.json["msg"] == "Successfully updated user password"

# admin user deletes other user
@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_changeUserPassword_valid_admin(client: Client, admin):
    res = client.post("/api/changeUserPassword", headers=admin, data={
                      "password": "adminPassword1!", "newPassword": "admin2Password!", "emailModify": "user@test.com"})
    assert res.status_code == 200
    assert res.json["msg"] == "Successfully updated user password"




# wrong password
@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_changeUserEmail_invalid_wrongPassword(client: Client, user):
    res = client.post("/api/changeUserEmail", headers=user,
                      data={"password": "userPassword2!", "newEmail": "user2@test.com"})
    assert res.status_code == 403
    assert res.json["msg"] == "Incorrect password provided"
    assert res.json["errorType"] == "auth"

# normal user who tries to modify other user
@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_changeUserEmail_invalid_noPermissions(client: Client, user):
    res = client.post("/api/changeUserEmail", headers=user, data={
                      "password": "userPassword1!", "newEmail": "user2@test.com", "emailModify": "admin@test.com"})
    assert res.status_code == 403
    assert res.json["msg"] == "You don't have permission to modify other users"
    assert res.json["errorType"] == "permission"

# admin user who tries to modify other user, but email is invalid
@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_changeUserEmail_invalid_wrongEmail(client: Client, admin):
    res = client.post("/api/changeUserEmail", headers=admin, data={
                      "password": "adminPassword1!", "newEmail": "abc2@xyz.com", "emailModify": "abc@xyz.com"})
    assert res.status_code == 400
    assert res.json["msg"] == "No user exists with that email"
    assert res.json["errorType"] == "notInDatabase"

# provided 'email' is not an email address
@pytest.mark.parametrize("client, email", [(("[]", "false"), "abcdefg"), (("[]", "false"), "user2"), (("[]", "false"), "user2@test"), (("[]", "false"), "user2@test."), (("[]", "false"), "@test.com")], indirect=["client"])
def test_changeUserEmail_invalid_invalidEmail1(client: Client, email: str, user):
    res = client.post("/api/changeUserEmail", headers=user,
                      data={"password": "userPassword1!", "newEmail": email})
    assert res.status_code == 400
    assert res.json["msg"] == f"'{email}' is not a valid email address"
    assert res.json["allowedEmailDomains"] == []
    assert res.json["errorType"] == "email"

# provided 'email's domain is not in 'allowedEmailDomains'
@pytest.mark.parametrize("client, email", [(("[ 'test.com' ]", "false"), "user2@test.de"), (("[ 'test.com' ]", "false"), "user2@sub.test.com")], indirect=["client"])
def test_changeUserEmail_invalid_invalidEmail2(client: Client, email: str, user):
    res = client.post("/api/changeUserEmail", headers=user,
                      data={"password": "userPassword1!", "newEmail": email})
    assert res.status_code == 400
    assert res.json["msg"] == f"'{email}' is not a valid email address"
    assert res.json["allowedEmailDomains"] == [ 'test.com' ]
    assert res.json["errorType"] == "email"

# email couldn't be sent
@pytest.mark.parametrize("client", [("[]", "false"), ("[ 'test.com' ]", "false"), ("[ 'test.com', 'sub.test.com' ]", "false")], indirect=True)
def test_changeUserEmail_invalid_brokenSMTP(client: Client, mockedSMTP, user):
    mockedSMTP.side_effect = smtplib.SMTPException

    res = client.post("/api/changeUserEmail", headers=user,
                      data={"password": "userPassword1!", "newEmail": "user2@test.com"})
    assert res.status_code == 400
    assert res.json["msg"] == "Failed to send activation email to user2@test.com. Email address may not exist"
    assert res.json["errorType"] == "email"

    #smtp stuff
    assert mockedSMTP.call_count == 1


# normal user modifies themselves
@pytest.mark.parametrize("client", [("[]", "false"), ("[ 'test.com' ]", "false"), ("[ 'test.com', 'sub.test.com' ]", "false")], indirect=True)
def test_changeUserEmail_valid_nonAdmin(client: Client, mockedSMTP, user):
    res = client.post("/api/changeUserEmail", headers=user,
                      data={"password": "userPassword1!", "newEmail": "user2@test.com"})
    assert res.status_code == 200
    assert res.json["msg"] == "Successfully requested email address change. Please confirm your new address by clicking on the link provided in the email we just sent you"

    #smtp stuff
    assert mockedSMTP.call_count == 1
    msg = mockedSMTP.mock_calls[3][1][0]
    assert msg["Subject"] == "Project-W account activation"
    assert msg["From"] == "alice@example.com"
    assert msg["To"] == "user2@test.com"
    body = msg.get_content()
    assert body.startswith("To activate your Project-W account")
    assert body.count("https://example.com/activate?token=")

@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_changeUserEmail_valid_admin(client: Client, mockedSMTP, admin):
    # admin user deletes other user
    res = client.post("/api/changeUserEmail", headers=admin, data={
                      "password": "adminPassword1!", "newEmail": "user2@test.com", "emailModify": "user@test.com"})
    assert res.status_code == 200
    assert res.json["msg"] == "Successfully requested email address change. Please confirm your new address by clicking on the link provided in the email we just sent you"

    #smtp stuff
    assert mockedSMTP.call_count == 1
    msg = mockedSMTP.mock_calls[3][1][0]
    assert msg["Subject"] == "Project-W account activation"
    assert msg["From"] == "alice@example.com"
    assert msg["To"] == "user2@test.com"
    body = msg.get_content()
    assert body.startswith("To activate your Project-W account")
    assert body.count("https://example.com/activate?token=")




@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_changeUserPassword_revokes_session(client: Client, user):
    # assume this succeeds, that's not what we're testing here
    res = client.post("/api/changeUserPassword", headers=user,
                      data={"password": "userPassword1!", "newPassword": "user2Password1!"})
    assert res.status_code == 200

    res = client.get("/api/userinfo", headers=user)
    # the request should fail because the jwt token has been revoked
    # by changing the user password
    assert 400 <= res.status_code < 500

@pytest.mark.parametrize("client", [("[]", "false")], indirect=True)
def test_changeUserEmail_revokes_session(client: Client, mockedSMTP, user):
    # assume this succeeds, that's not what we're testing here
    res = client.post("/api/changeUserEmail", headers=user,
                      data={"password": "userPassword1!", "newEmail": "user2@test.com"})
    assert res.status_code == 200

    msgBody = mockedSMTP.mock_calls[3][1][0].get_content()
    tokenLine = msgBody.split('\n')[2]
    token = tokenLine.partition("token=")[2]

    res = client.get("/api/activate", query_string={"token": token})
    assert res.status_code == 200

    res = client.get("/api/userinfo", headers=user)
    # the request should fail because the jwt token has been revoked.
    # by changing the user password
    assert 400 <= res.status_code < 500
