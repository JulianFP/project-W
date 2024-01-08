from dataclasses import dataclass
from typing import Tuple
from argon2 import PasswordHasher
from flask_sqlalchemy import SQLAlchemy
from smtplib import SMTP, SMTP_SSL
from email.message import EmailMessage
from project_W.logger import get_logger
from project_W.utils import encode_activation_token, decode_activation_token
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
) -> Tuple[str, int]:
    email_already_in_use = db.session.query(
        User.query.where(User.email == email).exists()).scalar()
    if email_already_in_use:
        return "E-Mail is already used by another account", 400
    if not send_activation_email(email, email):
        return f"Failed to send activation email to {email}. Email address may not exist", 400

    logger.info(f" -> Created user with email {email}")
    db.session.add(
        User(email=email, password_hash=hasher.hash(password), is_admin=is_admin, activated=False))
    db.session.commit()

    return f"Successful signup for {email}. Please activate your account be clicking on the link provided in the email we just sent you", 200


def activate_user(token: str) -> Tuple[str, int]:
    secret_key = flask.current_app.config["JWT_SECRET_KEY"]
    emails = decode_activation_token(token, secret_key)
    old_email = emails["old_email"]
    new_email = emails["new_email"]

    if emails is None:
        logger.info("  -> Invalid user activation token")
        return "Invalid or expired activation link", 400
    logger.info(f"  -> activation request for email '{new_email}'")
    user = db.session.execute(
        db.select(User).filter(User.email == old_email)
    ).scalar_one_or_none()
    if user is None:
        logger.info(f"  -> Unknown email address '{old_email}' for user activation token")
        return f"Unknown email address {old_email}", 400
    if user.activated is True and old_email == new_email:
        logger.info(f"  -> User with email {old_email} already activated")
        return f"Account for {old_email} is already activated", 400
    user.activated = True
    user.set_email(new_email) #update email address (in case activation got issued for changed email address)
    db.session.commit()
    return f"Account {new_email} activated", 200


def delete_user(
    user: User
) -> Tuple[str, int]:
    db.session.delete(user)
    db.session.commit()
    logger.info(f" -> Deleted user with email {user.email}")

    return (f"Successfully deleted user with email {user.email}"), 200


def send_activation_email(old_email: str, new_email: str) -> bool:
    config = flask.current_app.config
    secret_key = config["JWT_SECRET_KEY"]
    token = encode_activation_token(old_email, new_email, secret_key)
    url = f"{config['url']}/api/activate?token={token}"
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

def is_valid_email(email: str) -> bool:
    allowedDomains = flask.current_app.config["loginSecurity"]["allowedEmailDomains"]
    pattern = r"^\S+@"
    if allowedDomains == []: pattern += r"([a-z0-9\-]+\.)+[a-z0-9\-]+"
    else: pattern += r"(" + "|".join(allowedDomains) + r")"
    pattern += r"$"
    return re.match(pattern, email) is not None

def is_valid_password(password: str) -> bool:
    return re.match(r"^(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9])(?=.*[^a-zA-Z0-9]).{12,}$", password) is not None

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
