import argon2
from project_W.model import Job, StatusEnum, User, db

def add_test_users(app):
    ph = argon2.PasswordHasher()
    with app.app_context():
        # add users for tests
        for name, is_admin, id in [("admin", True, 1), ("user", False, 2)]:
            email = f"{name}@test.com"
            db.session.add(
                User(
                    id=id,
                    email=email,
                    password_hash=ph.hash(name),
                    is_admin=is_admin,
                )
            )
            db.session.add(
                Job(
                    user_id=id,
                    file_name="sample.mp3",
                    audio_data=b"",
                    status=StatusEnum.PENDING_RUNNER,
                )
            )
        db.session.commit()