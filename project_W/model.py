from dataclasses import dataclass
import secrets
from typing import Tuple
from argon2 import PasswordHasher
import argon2
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import exists

from project_W.logger import get_logger

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

    def set_password_unchecked(self, new_password: str):
        self.invalidate_session_tokens()
        self.password_hash = hasher.hash(new_password)
        db.session.commit()

    def set_password(self, current_password: str, new_password: str) -> bool:
        if self.check_password(current_password):
            self.set_password_unchecked(new_password)
            return True
        return False

    def set_email(self, new_email: str):
        self.email = new_email
        self.invalidate_session_tokens()

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

    logger.info(f" -> Created user with email {email}")
    db.session.add(
        User(email=email, password_hash=hasher.hash(password), is_admin=is_admin))
    db.session.commit()

    return "Successfully created user. Use /api/login to authenticate yourself", 200


def delete_user(
    user: User
) -> Tuple[str, int]:
    db.session.delete(user)
    db.session.commit()
    logger.info(f" -> Deleted user with email {user.email}")

    return (f"Successfully deleted user with email {user.email}"), 200


def update_user_password(
    user: User, new_password: str
) -> Tuple[str, int]:
    user.set_password_unchecked(new_password)
    db.session.commit()
    logger.info(f" -> Updated password of user {user.email}")
    return "Successfully updated user password", 200


def update_user_email(
    user: User, new_email: str
) -> Tuple[str, int]:
    user.set_email(new_email)
    db.session.commit()
    logger.info(f" -> Updated email of user {user.email}")
    return "Successfully updated user email", 200
