import argon2
from project_W.model import User, db

def add_test_users(app):
    ph = argon2.PasswordHasher()
    with app.app_context():
        # add users for tests
        for name, is_admin in [("admin", True), ("user", False)]:
            email = f"{name}@test.com"
            db.session.add(
                User(
                    email=email,
                    password_hash=ph.hash(name),
                    is_admin=is_admin,
                    activated=True
                )
            )
        db.session.commit()
