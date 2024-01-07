from dataclasses import dataclass
import secrets
from typing import Dict, List, Tuple
from argon2 import PasswordHasher
import argon2
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
import enum

from project_W.logger import get_logger

db = SQLAlchemy()
hasher = PasswordHasher()
logger = get_logger("project-W")


@dataclass
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.Text, nullable=False, unique=True)
    password_hash = db.Column(db.Text, nullable=False)
    # We use this key together with JWT_SECRET_KEY to generate session tokens.
    # That way, we can easily invalidate all existing session tokens by changing
    # this value.
    user_key = db.Column(db.Text, nullable=False,
                         default=lambda: secrets.token_urlsafe(16))
    is_admin = db.Column(db.Boolean, nullable=False)

    jobs = relationship("Job", order_by="Job.id", backref="user", cascade="all,delete-orphan")

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


class StatusEnum(enum.StrEnum):
    # The backend has received the job request but no
    # runner has been assigned yet
    PENDING_RUNNER = "pending_runner"
    # A runner has been assigned, and is currently processing
    # the request
    RUNNER_IN_PROGRESS = "runner_in_progress"
    # The runner successfully completed the job and
    # the transcript is ready for retrieval
    SUCCESS = "success"
    # There was an error during the processing of the request
    FAILED = "failed"


@dataclass
class Job(db.Model):
    __tablename__ = "jobs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, ForeignKey("users.id"), index=True, nullable=False)
    file_name = db.Column(db.Text)
    audio_data = db.Column(db.BLOB)
    model = db.Column(db.Text)
    language = db.Column(db.Text)
    status = db.Column(db.Enum(StatusEnum))
    transcript = db.Column(db.Text)
    error_msg = db.Column(db.Text)
    # TODO Add some form of runner token/tag system


def submit_job(user: User, file_name: str | None, audio: bytes, model: str | None, language: str | None) -> Job:
    job = Job(
        user_id=user.id,
        file_name=file_name,
        audio_data=audio,
        model=model,
        language=language,
        status=StatusEnum.PENDING_RUNNER,
    )

    db.session.add(job)
    db.session.commit()

    logger.info(f"User {user.email} submitted job with file {file_name}")
    logger.info(f" -> Assigned job id {job.id}")

    return job


def list_job_ids_for_user(user: User) -> List[int]:
    """Returns a list of all the job IDs associated with this user"""
    return [job.id for job in user.jobs]


def list_job_ids_for_all_users() -> Dict[int, List[int]]:
    """For each user, returns a list of all job IDs associated with that user"""
    return {user.id: list_job_ids_for_user(user) for user in db.session.query(User)}
