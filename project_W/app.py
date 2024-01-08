
import datetime
import os
import secrets
from typing import Optional
from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, create_access_token, current_user, jwt_required
from .logger import get_logger
from .model import Job, User, add_new_user, create_runner, delete_user, \
    get_runner_by_token, list_job_ids_for_all_users, list_job_ids_for_user, \
    submit_job, update_user_password, update_user_email, db


def create_app(db_path: str = ".") -> Flask:
    logger = get_logger("project-W")
    app = Flask("project-W")

    jwt_secret_key = os.environ.get("JWT_SECRET_KEY")
    if jwt_secret_key is not None and len(jwt_secret_key) > 16:
        logger.info("Setting JWT_SECRET_KEY from supplied env var")
        JWT_SECRET_KEY = jwt_secret_key
    else:
        logger.warning(
            "JWT_SECRET_KEY env var not set or too short: generating random secret key"
        )
        # new secret key -> invalidates any existing tokens
        JWT_SECRET_KEY = secrets.token_urlsafe(64)

    app.config["JWT_SECRET_KEY"] = JWT_SECRET_KEY

    # tokens are by default valid for 1 hour
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = datetime.timedelta(minutes=60)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}/database.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    jwt = JWTManager(app)
    db.init_app(app)

    @jwt.user_identity_loader
    def user_identity_loader(user: User):
        return user.id

    @jwt.user_lookup_loader
    def user_lookup_loader(_jwt_header, jwt_data):
        id = jwt_data["sub"]
        return User.query.where(User.id == id).one_or_none()

    @jwt.encode_key_loader
    def encode_key_loader(user: User):
        return JWT_SECRET_KEY + user.user_key

    @jwt.decode_key_loader
    def decode_key_loader(_jwt_header, jwt_data):
        id = jwt_data.get("sub")
        user: User = User.query.where(User.id == id).one_or_none()
        if user:
            return JWT_SECRET_KEY + user.user_key

        # If the user doesn't exist then the token will fail anyways
        return JWT_SECRET_KEY

    @app.post("/api/signup")
    def signup():
        email = request.form['email']
        password = request.form['password']
        logger.info(f"Signup request from {email}")
        message, code = add_new_user(email, password, False)
        return jsonify(message=message), code

    @app.post("/api/login")
    def login():
        email = request.form['email']
        password = request.form['password']
        logger.info(f"Login request from {email}")

        user: Optional[User] = User.query.where(
            User.email == email).one_or_none()

        if not (user and user.check_password(password)):
            logger.info(" -> incorrect credentials")
            return jsonify(message="Incorrect credentials provided"), 400

        logger.info(" -> login successful, returning JWT token")
        return jsonify(access_token=create_access_token(user))

    @app.get("/api/userinfo")
    @jwt_required()
    def userinfo():
        user: User = current_user
        if (email := request.args.get("email", type=str)):
            if not user.is_admin:
                logger.info(
                    f"Non-admin tried to access user info of {email}, denied")
                return jsonify(message="You don't have permission to view other accounts' user info"), 403
            logger.info(f"Admin requested user info for {user.email}")
            user = User.query.where(User.email == email).one_or_none()
            if not user:
                logger.info(" -> Invalid user email")
                return jsonify(message="No user exists with that email"), 400
        else:
            logger.info(f"Requested user info for {user.email}")
        return jsonify(email=user.email, is_admin=user.is_admin)

    @app.post("/api/deleteUser")
    @jwt_required()
    def deleteUser():
        thisUser: User = current_user
        toDelete: User = current_user

        # ask for password as confirmation
        password = request.form['password']
        if not thisUser.check_password(password):
            logger.info(" -> incorrect password")
            return jsonify(message="Incorrect password provided"), 403

        if 'emailDelete' in request.form:
            specifiedEmail = request.form['emailDelete']
            specifiedUser = User.query.where(
                User.email == specifiedEmail).one_or_none()
            if not thisUser.is_admin:
                logger.info(
                    f"Non-admin tried to delete user {specifiedEmail}, denied")
                return jsonify(message="You don't have permission to delete other users"), 403
            elif not specifiedUser:
                logger.info(" -> Invalid user email")
                return jsonify(message="No user exists with that email"), 400
            else:
                toDelete = specifiedUser

        logger.info(f"user deletion request from {thisUser.email} for user {toDelete.email}")
        message, code = delete_user(toDelete)
        return jsonify(message=message), code

    @app.post("/api/changeUserPassword")
    @jwt_required()
    def changeUserPassword():
        thisUser: User = current_user
        toModify: User = current_user

        # ask for password as confirmation
        password = request.form['password']
        if not thisUser.check_password(password):
            logger.info(" -> incorrect password")
            return jsonify(message="Incorrect password provided"), 403

        if 'emailModify' in request.form:
            specifiedEmail = request.form['emailModify']
            specifiedUser = User.query.where(
                User.email == specifiedEmail).one_or_none()
            if not thisUser.is_admin:
                logger.info(
                    f"Non-admin tried to delete user {specifiedEmail}, denied")
                return jsonify(message="You don't have permission to modify other users"), 403
            elif not specifiedUser:
                logger.info(" -> Invalid user email")
                return jsonify(message="No user exists with that email"), 400
            else:
                toDelete = specifiedUser

        new_password = request.form['new_password']
        logger.info(f"request to modify user password from {thisUser.email} for user {toModify.email}")
        message, code = update_user_password(toModify, new_password)
        return jsonify(message=message), code

    @app.post("/api/changeUserEmail")
    @jwt_required()
    def changeUserEmail():
        thisUser: User = current_user
        toModify: User = current_user

        # ask for password as confirmation
        password = request.form['password']
        if not thisUser.check_password(password):
            logger.info(" -> incorrect password")
            return jsonify(message="Incorrect password provided"), 403

        if 'emailModify' in request.form:
            specifiedEmail = request.form['emailModify']
            specifiedUser = User.query.where(
                User.email == specifiedEmail).one_or_none()
            if not thisUser.is_admin:
                logger.info(
                    f"Non-admin tried to delete user {specifiedEmail}, denied")
                return jsonify(message="You don't have permission to modify other users"), 403
            elif not specifiedUser:
                logger.info(" -> Invalid user email")
                return jsonify(message="No user exists with that email"), 400
            else:
                toDelete = specifiedUser

        new_email = request.form['new_email']
        logger.info(f"request to modify user email from {thisUser.email} for user {toModify.email}")
        message, code = update_user_email(toModify, new_email)
        return jsonify(message=message), code

    @app.post("/api/jobs/submit")
    @jwt_required()
    def submitJob():
        user: User = current_user
        file = request.files["file"]
        file.stream.seek(0)
        file_name = file.filename
        audio = file.stream.read()
        model = request.form.get("model")
        language = request.form.get("model")
        job = submit_job(user, file_name, audio, model, language)
        return jsonify(job_id=job.id)

    @app.get("/api/jobs/list")
    @jwt_required()
    def listJobs():
        user: User = current_user
        requested_user = user
        if "email" in request.args or "all" in request.args:
            if not user.is_admin:
                logger.info("Non-admin tried to list other users' jobs, denied")
                return jsonify(message="You don't have permission to list other users' jobs"), 403

            if request.args.get("all", type=bool):
                ids_by_user = list_job_ids_for_all_users()
                return jsonify([{"user_id": user_id, "job_ids": job_ids}
                                for (user_id, job_ids) in ids_by_user.items()]), 200

            email = request.args["email"]
            requested_user = User.query.where(User.email == email).one_or_none()
            if not requested_user:
                logger.info(f"Admin tried to list jobs of nonexistent user {email}")
                return jsonify(message="No user exists with that email"), 400

        return jsonify(job_ids=list_job_ids_for_user(requested_user)), 200

    @app.get("/api/jobs/status")
    @jwt_required()
    def jobStatus():
        user: User = current_user
        job_id = request.args['job_id']
        job: Job = Job.query.where(Job.id == job_id).one_or_none()
        # Technically, job IDs aren't secret, so leaking whether they exist
        # isn't a big deal, but it still seems cleaner this way
        if not job:
            if user.is_admin:
                return jsonify(message="There exists no job with that id"), 404
            return jsonify(message="You don't have permission to access this job"), 403
        if job.user_id != user.id and not user.is_admin:
            return jsonify(message="You don't have permission to access this job"), 403
        return jsonify(status=job.status)

    @app.get("/api/runners/create")
    def createRunner():
        token, runner = create_runner()
        logger.info(f"Created runner with label '{runner.label}'")
        return token

    @app.post("/api/runners/heartbeat")
    def heartbeat():
        token = request.form["runner_token"]
        runner = get_runner_by_token(token)
        print(runner)
        return jsonify({})

    with app.app_context():
        db.create_all()

    return app
