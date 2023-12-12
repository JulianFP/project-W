
from typing import Dict
from flask import Flask
from werkzeug import Client

from tests import get_auth_headers


def test_signup_invalid(client: Client):
    # missing form data
    res = client.post("/api/signup")
    # leads to a flask error
    assert 400 <= res.status_code < 500

    # user email is already in use
    res = client.post(
        "/api/signup", data={"email": "user@test.com", "password": "test"})
    assert res.status_code == 400
    assert res.json["message"] == "E-Mail is already used by another account"

    # TODO: Add more invalid cases once we have email/password restrictions


def test_signup_valid(client: Client):
    res = client.post(
        "/api/signup", data={"email": "user2@test.com", "password": "user2"})
    assert res.status_code == 200
    assert res.json["message"] == "Successfully created user. Use /api/login to authenticate yourself"


def test_login_invalid(client: Client):
    # missing form data
    res = client.post("/api/login")
    assert 400 <= res.status_code < 500

    # unknown email
    res = client.post("/api/login", data={"email": "", "password": ""})
    assert res.status_code == 400
    assert res.json["message"] == "Incorrect credentials provided"

    # wrong password
    res = client.post(
        "/api/login", data={"email": "user@test.com", "password": ""})
    assert res.status_code == 400
    assert res.json["message"] == "Incorrect credentials provided"


def test_login_valid(client: Client):
    email = "user@test.com"
    password = "user"
    response = client.post(
        "/api/login", data={"email": email, "password": password})
    assert response.status_code == 200
    assert "access_token" in response.json


def test_userinfo_invalid(client: Client, user, admin):
    # non-admins can't access other users' infos
    res = client.get("/api/userinfo", headers=user,
                     query_string={"email": "admin@test.com"})
    assert res.status_code == 403
    assert res.json["message"] == "You don't have permission to view other accounts' user info"

    # can't access non-existent user info
    res = client.get("/api/userinfo", headers=admin,
                     query_string={"email": "fake@test.com"})
    assert res.status_code == 400
    assert res.json["message"] == "No user exists with that email"


def test_userinfo_valid(client: Client, user, admin):
    # non-admins can access their own user info
    res = client.get("/api/userinfo", headers=user)
    assert res.status_code == 200
    assert res.json["email"] == "user@test.com"
    assert res.json["is_admin"] == False

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


def test_deleteUser_invalid(client: Client, user, admin):
    # wrong password
    res = client.post("/api/deleteUser", headers=user,
                      data={"password": "xyz"})
    assert res.status_code == 403
    assert res.json["message"] == "Incorrect password provided"

    # normal user who tries to delete other user
    res = client.post("/api/deleteUser", headers=user,
                      data={"password": "user", "emailDelete": "admin@test.com"})
    assert res.status_code == 403
    assert res.json["message"] == "You don't have permission to delete other users"

    # admin user who tries to delete other user, but email is invalid
    res = client.post("/api/deleteUser", headers=admin,
                      data={"password": "admin", "emailDelete": "abc@xyz.com"})
    assert res.status_code == 400
    assert res.json["message"] == "No user exists with that email"


def test_deleteUser_valid_normal(client: Client, user):
    # normal user deletes themselves
    res = client.post("/api/deleteUser", headers=user,
                      data={"password": "user"})
    assert res.status_code == 200
    assert res.json["message"] == "Successfully deleted user with email user@test.com"


def test_deleteUser_valid_admin(client: Client, admin):
    # admin user deletes other user
    res = client.post("/api/deleteUser", headers=admin,
                      data={"password": "admin", "emailDelete": "user@test.com"})
    assert res.status_code == 200
    assert res.json["message"] == "Successfully deleted user with email user@test.com"


def test_changeUserPassword_invalid(client: Client, user, admin):
    # wrong password
    res = client.post("/api/changeUserPassword", headers=user,
                      data={"password": "xyz", "new_password": "user2"})
    assert res.status_code == 403
    assert res.json["message"] == "Incorrect password provided"

    # normal user who tries to modify other user
    res = client.post("/api/changeUserPassword", headers=user, data={
                      "password": "user", "new_password": "user2", "emailModify": "admin@test.com"})
    assert res.status_code == 403
    assert res.json["message"] == "You don't have permission to modify other users"

    # admin user who tries to modify other user, but email is invalid
    res = client.post("/api/changeUserPassword", headers=admin, data={
                      "password": "admin", "new_password": "abc2", "emailModify": "abc@xyz.com"})
    assert res.status_code == 400
    assert res.json["message"] == "No user exists with that email"


def test_changeUserPassword_valid_normal(client: Client, user):
    # normal user modifies themselves
    res = client.post("/api/changeUserPassword", headers=user,
                      data={"password": "user", "new_password": "user2"})
    assert res.status_code == 200
    assert res.json["message"] == "Successfully updated user password"


def test_changeUserPassword_valid_admin(client: Client, admin):
    # admin user deletes other user
    res = client.post("/api/changeUserPassword", headers=admin, data={
                      "password": "admin", "new_password": "user2", "emailDelete": "user@test.com"})
    assert res.status_code == 200
    assert res.json["message"] == "Successfully updated user password"


def test_changeUserEmail_invalid(client: Client, user, admin):
    # wrong password
    res = client.post("/api/changeUserEmail", headers=user,
                      data={"password": "xyz", "new_email": "user2@test.com"})
    assert res.status_code == 403
    assert res.json["message"] == "Incorrect password provided"

    # normal user who tries to modify other user
    res = client.post("/api/changeUserEmail", headers=user, data={
                      "password": "user", "new_email": "user2@test.com", "emailModify": "admin@test.com"})
    assert res.status_code == 403
    assert res.json["message"] == "You don't have permission to modify other users"

    # admin user who tries to modify other user, but email is invalid
    res = client.post("/api/changeUserEmail", headers=admin, data={
                      "password": "admin", "new_email": "abc2@xyz.com", "emailModify": "abc@xyz.com"})
    assert res.status_code == 400
    assert res.json["message"] == "No user exists with that email"


def test_changeUserEmail_valid_normal(client: Client, user):
    # normal user modifies themselves
    res = client.post("/api/changeUserEmail", headers=user,
                      data={"password": "user", "new_email": "user2@test.com"})
    assert res.status_code == 200
    assert res.json["message"] == "Successfully updated user email"


def test_changeUserEmail_valid_admin(client: Client, admin):
    # admin user deletes other user
    res = client.post("/api/changeUserEmail", headers=admin, data={
                      "password": "admin", "new_email": "user2@test.com", "emailDelete": "user@test.com"})
    assert res.status_code == 200
    assert res.json["message"] == "Successfully updated user email"


def test_changeUserPassword_revokes_session(client: Client, user):
    # assume this succeeds, that's not what we're testing here
    res = client.post("/api/changeUserPassword", headers=user,
                      data={"password": "user", "new_password": "user2"})
    assert res.status_code == 200

    res = client.get("/api/userinfo", headers=user)
    # the request should fail because the jwt token has been revoked
    # by changing the user password
    assert 400 <= res.status_code < 500


def test_changeUserEmail_revokes_session(client: Client, user):
    # assume this succeeds, that's not what we're testing here
    res = client.post("/api/changeUserEmail", headers=user,
                      data={"password": "user", "new_email": "user2@test.com"})
    assert res.status_code == 200

    res = client.get("/api/userinfo", headers=user)
    # the request should fail because the jwt token has been revoked.
    # by changing the user password
    assert 400 <= res.status_code < 500
