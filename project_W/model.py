from dataclasses import dataclass
from typing import Tuple, Optional
from argon2 import PasswordHasher
from flask import Response, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import current_user
from smtplib import SMTP, SMTP_SSL
from email.message import EmailMessage
from functools import wraps
from project_W.logger import get_logger
from project_W.utils import encode_activation_token, decode_activation_token, encode_password_reset_token, decode_password_reset_token
import secrets, ssl, argon2, flask, re

db = SQLAlchemy()
hasher = PasswordHasher()
logger = get_logger("project-W")


@dataclass
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.Text, nullable=False, unique=True)
    password_hash = db.Column(db.Text, nullable=False)
    # We use this key together with JWT_SECRET_KEY to generate session tokens.
    # That way, we can easily invalidate all existing session tokens by changing
    # this value.
    user_key = db.Column(db.Text, nullable=False,
                         default=lambda: secrets.token_urlsafe(16))
    is_admin = db.Column(db.Boolean, nullable=False)
    activated = db.Column(db.Boolean, nullable=False)

    def set_password_unchecked(self, new_password: str):
        self.invalidate_session_tokens()
        self.password_hash = hasher.hash(new_password)
        db.session.commit()
        logger.info(f" -> Updated password of user {self.email}")

    def set_email(self, new_email: str):
        self.invalidate_session_tokens()
        old_email = self.email
        self.email = new_email
        db.session.commit()
        logger.info(f" -> Updated email from {old_email} to {self.email}")

    def check_password(self, password: str) -> bool:
        try:
            hasher.verify(self.password_hash, password)
        except argon2.exceptions.VerificationError:
            return False
        if hasher.check_needs_rehash(self.password_hash):
            self.password_hash = hasher.hash(password)
            db.session.commit()
        return True

    def invalidate_session_tokens(self):
        self.user_key = secrets.token_urlsafe(16)
        db.session.commit()


def add_new_user(
        email: str, password: str, is_admin: bool
) -> Tuple[Response, int]:
    email_already_in_use = db.session.query(
        User.query.where(User.email == email).exists()).scalar()
    if email_already_in_use:
        return jsonify(msg="E-Mail is already used by another account", errorType="email"), 400
    if not send_activation_email(email, email):
        return jsonify(msg=f"Failed to send activation email to {email}. Email address may not exist", errorType="email"), 400

    logger.info(f" -> Created user with email {email}")
    db.session.add(
        User(email=email, password_hash=hasher.hash(password), is_admin=is_admin, activated=False))
    db.session.commit()

    return jsonify(msg=f"Successful signup for {email}. Please activate your account be clicking on the link provided in the email we just sent you"), 200


def activate_user(token: str) -> Tuple[Response, int]:
    secret_key = flask.current_app.config["JWT_SECRET_KEY"]
    emails = decode_activation_token(token, secret_key)

    if emails is None:
        logger.info("  -> Invalid user activation token")
        return jsonify(msg="Invalid or expired activation link", errorType="auth"), 400

    old_email = emails["old_email"]
    new_email = emails["new_email"]

    logger.info(f"  -> activation request for email '{new_email}'")
    user: Optional[User] = User.query.where(
        User.email == old_email).one_or_none()
    if user is None:
        logger.info(f"  -> Invalid user email '{old_email}' for user activation token")
        return jsonify(msg=f"No user with email {old_email} exists", errorType="notInDatabase"), 400
    if user.activated is True and old_email == new_email:
        logger.info(f"  -> User with email {old_email} already activated")
        return jsonify(msg=f"Account for {old_email} is already activated", errorType="operation"), 400
    user.activated = True
    user.set_email(new_email) #update email address (in case activation got issued for changed email address)
    db.session.commit()
    return jsonify(msg=f"Account {new_email} activated"), 200


def reset_user_password(token: str, newPassword: str) -> Tuple[Response, int]:
    secret_key = flask.current_app.config["JWT_SECRET_KEY"]
    email = decode_password_reset_token(token, secret_key)

    if email is None:
        logger.info("  -> Invalid password reset token")
        return jsonify(msg="Invalid or expired password reset link", errorType="auth"), 400
    
    logger.info(f"  -> initiated password reset for email '{email}'")
    user: Optional[User] = User.query.where(
        User.email == email).one_or_none()
    if user is None:
        logger.info(f"  -> Unknown email address '{email}' for password reset token")
        return jsonify(msg=f"Unknown email address {email}", errorType="notInDatabase"), 400
    user.set_password_unchecked(newPassword)
    db.session.commit()
    logger.info(f"  -> password changed via password reset for user {email}")
    return jsonify(msg=f"password changed successfully"), 200


def delete_user(
    user: User
) -> Tuple[Response, int]:
    db.session.delete(user)
    db.session.commit()
    logger.info(f" -> Deleted user with email {user.email}")

    return jsonify(msg=f"Successfully deleted user with email {user.email}"), 200


def is_valid_email(email: str) -> bool:
    allowedDomains = flask.current_app.config["loginSecurity"]["allowedEmailDomains"]
    pattern = r"^\S+@"
    if not allowedDomains: pattern += r"([a-z0-9\-]+\.)+[a-z0-9\-]+"
    else: pattern += r"(" + "|".join(allowedDomains) + r")"
    pattern += r"$"
    return re.match(pattern, email) is not None

def is_valid_password(password: str) -> bool:
    return re.match(r"^(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9])(?=.*[^a-zA-Z0-9]).{12,}$", password) is not None


def send_activation_email(old_email: str, new_email: str) -> bool:
    config = flask.current_app.config
    secret_key = config["JWT_SECRET_KEY"]
    token = encode_activation_token(old_email, new_email, secret_key)
    url = f"{config['clientURL']}/activate?token={token}"
    logger.info(f" -> Activation url for email {new_email}: {url}")
    msg_body = (
        f"To activate your Project-W account, "
        f"please confirm your email address by clicking on the following link:\n\n"
        f"{url}\n\n"
        f"This link will expire within the next 24 hours. "
        f"After this period you will have to request a new activation email over the website\n\n"
        f"If you did not sign up for an account please disregard this email."
    )
    msg_subject = "Project-W account activation"
    return _send_email(new_email, msg_body, msg_subject)

def send_password_reset_email(email: str) -> bool:
    config = flask.current_app.config
    secret_key = config["JWT_SECRET_KEY"]
    token = encode_password_reset_token(email, secret_key)
    url = f"{config['clientURL']}/resetPassword?token={token}"
    logger.info(f" -> Password Reset url for email {email}: {url}")
    msg_body = (
        f"To reset the password of your Project-W account, "
        f"please open the following link and enter a new password:\n\n"
        f"{url}\n\n"
        f"This link will expire within the next hour. "
        f"After this period you will have to request a new password reset email over the website\n\n"
        f"If you did not request a password reset then you can disregard this email"
    )
    msg_subject = "Project-W password reset request"
    return _send_email(email, msg_body, msg_subject)

def _send_email(
        receiver: str, msg_body: str, msg_subject: str
    ) -> bool:
    smtpConfig = flask.current_app.config["smtpServer"]

    msg = EmailMessage()
    msg.set_content(msg_body)
    msg["Subject"] = msg_subject
    msg["From"] = smtpConfig["senderEmail"]
    msg["To"] = receiver
    context = ssl.create_default_context()

    try:
        #default instance for unencrypted and starttls 
        #ssl encrypts from beginning and requires a different instance
        smtpInstance = (SMTP_SSL(smtpConfig["domain"], smtpConfig["port"], context=context) 
            if smtpConfig["secure"] == "ssl" 
            else SMTP(smtpConfig["domain"], smtpConfig["port"]))

        with smtpInstance as server:
            if smtpConfig["secure"] == "starttls": 
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
            server.login(smtpConfig["username"], smtpConfig["password"])
            server.send_message(msg)
            logger.info(f" -> successfully sent email to {receiver}")

        return True

    except Exception as e:
        logger.error(f" -> Error sending email to {receiver}: {e}")
        return False


#some additional wraps for api routes
#if user should be activated to use this route
def activatedRequired(f):
    @wraps(f)
    def decoratedFunction(*args, **kwargs):
        user: User = current_user
        if not user.activated:
            return jsonify(msg="Your account is not activated. Please activate your user account to use this feature.", errorType="permission"), 403
        else: return f(*args, **kwargs)
    return decoratedFunction

#if user should need to confirm their identity by entering their password
def confirmIdentity(f):
    @wraps(f)
    def decoratedFunction(*args, **kwargs):
        user: User = current_user
        password = request.form['password']
        if not user.check_password(password):
            logger.info(" -> incorrect password")
            return jsonify(msg="Incorrect password provided", errorType="auth"), 403
        else: return f(*args, **kwargs)
    return decoratedFunction

#if admins can change other users with 'emailModify' over same route as users can change themselves 
#will return user to be modified. This is either 'emailModify' or current_user 
def emailModifyForAdmins(f):
    @wraps(f)
    def decoratedFunction(*args, **kwargs):
        user: User = current_user
        toModify: User = current_user

        if 'emailModify' in request.form:
            specifiedEmail = request.form['emailModify']
            specifiedUser = User.query.where(
                User.email == specifiedEmail).one_or_none()
            if not user.is_admin:
                logger.info(
                    f"Non-admin tried to modify users {specifiedEmail} email, denied")
                return jsonify(msg="You don't have permission to modify other users", errorType="permission"), 403
            elif not specifiedUser:
                logger.info(" -> Invalid user email")
                return jsonify(msg="No user exists with that email", errorType="notInDatabase"), 400
            else:
                toModify = specifiedUser

        kwargs["toModify"] = toModify
        return f(*args, **kwargs)
    return decoratedFunction
