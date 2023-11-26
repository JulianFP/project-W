from dataclasses import dataclass
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
    is_admin = db.Column(db.Boolean, nullable=False)

    def set_password_unchecked(self, new_password: str):
        self.password_hash = hasher.hash(new_password)
        db.session.commit()

    def set_password(self, current_password: str, new_password: str) -> bool:
        if self.check_password(current_password):
            self.set_password_unchecked(new_password)
            return True
        return False

    def check_password(self, password: str) -> bool:
        try:
            hasher.verify(self.password_hash, password)
        except argon2.exceptions.VerificationError:
            return False
        if hasher.check_needs_rehash(self.password_hash):
            self.password_hash = hasher.hash(password)
            db.session.commit()
        return True


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
