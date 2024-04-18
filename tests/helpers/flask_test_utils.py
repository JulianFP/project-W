import argon2
from project_W.model import InputFile, Job, User, db


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
                    password_hash=ph.hash(name + "Password1!"),
                    is_admin=is_admin,
                    activated=True
                )
            )
            db.session.add(
                Job(
                    user_id=id,
                    file_name="sample.mp3",
                    file=InputFile(
                        audio_data=b"",
                    )
                )
            )
        db.session.commit()
