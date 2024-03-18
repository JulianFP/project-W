import base64
import datetime
import secrets
from typing import Optional
from pathlib import Path
from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, create_access_token, current_user, jwt_required

from project_W.utils import auth_token_from_req


from .logger import get_logger
from .model import Job, User, add_new_user, create_runner, delete_user, \
    get_runner_by_token, list_job_ids_for_all_users, list_job_ids_for_user, \
    submit_job, db, activate_user, send_activation_email, send_password_reset_email, reset_user_password, is_valid_email, is_valid_password
from .config import loadConfig
from .runner_manager import RunnerManager

def create_app(customConfigPath: Optional[str] = None) -> Flask:
    logger = get_logger("project-W")
    app = Flask("project-W")

    #load config from additionalPaths (if not None) + defaultSearchDirs
    if customConfigPath is None:
        app.config.update(loadConfig())
    else:
        path = Path(customConfigPath)
        if not path.is_dir(): path = path.parent
        app.config.update(loadConfig(additionalPaths=[ path ]))

    #check syntax of JWT_SECRET_KEY and update if necessary
    JWT_SECRET_KEY = app.config["loginSecurity"]["sessionSecretKey"]
    if JWT_SECRET_KEY is not None and len(JWT_SECRET_KEY) > 16:
        logger.info("Setting JWT_SECRET_KEY from supplied config or env var")
    else:
        logger.warning(
            "JWT_SECRET_KEY not set or too short: generating random secret key"
        )
        # new secret key -> invalidates any existing tokens
        JWT_SECRET_KEY = secrets.token_urlsafe(64)
    app.config["JWT_SECRET_KEY"] = JWT_SECRET_KEY

    # tokens are by default valid for 1 hour
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = datetime.timedelta(minutes=app.config["loginSecurity"]["sessionExpirationTimeMinutes"])
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{app.config['databasePath']}/database.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    jwt = JWTManager(app)
    db.init_app(app)

    runner_manager = RunnerManager(app)

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
        if app.config["loginSecurity"]["disableSignup"]:
            return jsonify(msg="signup of new accounts is disabled on this server"), 400

        email = request.form['email']
        password = request.form['password']
        logger.info(f"Signup request from {email}")

        if not is_valid_email(email): 
            return jsonify(msg=f"'{email}' is not a valid email address", allowedEmailDomains=app.config["loginSecurity"]["allowedEmailDomains"]), 400
        if not is_valid_password(password): 
            return jsonify(msg="password invalid. The password needs to have at least one lowercase letter, uppercase letter, number, special character and at least 12 characters in total"), 400

        message, code = add_new_user(email, password, False)
        return jsonify(msg=message), code

    @app.get("/api/activate")
    def activate():
        msg, code = "", 0
        if(token := request.args.get("token", type=str)):
            msg, code = activate_user(token)
        else: msg, code = "You need a token to activate a users email", 400
        return jsonify(msg=msg), code

    @app.post("/api/login")
    def login():
        email = request.form['email']
        password = request.form['password']
        logger.info(f"Login request from {email}")

        user: Optional[User] = User.query.where(
            User.email == email).one_or_none()

        if not (user and user.check_password(password)):
            logger.info(" -> incorrect credentials")
            return jsonify(msg="Incorrect credentials provided"), 400

        logger.info(" -> login successful, returning JWT token")
        return jsonify(accessToken=create_access_token(user))

    @app.post("/api/requestPasswordReset")
    def requestPasswordReset():
        email = request.form['email']
        logger.info(f"Password reset request for email {email}")
        msg, code = f"If an account with the address {email} exists, then we sent a password reset email to this address. Please check your emails", 200

        user: Optional[User] = User.query.where(
            User.email == email).one_or_none()
        if user is None:
            #do not change the output in this case since that would allow anybody to probe for emails which have an account here
            logger.info(f"  -> password reset request for unknown email address '{email}'")
        elif not send_password_reset_email(email):
            msg, code = f"Failed to send password reset email to {email}.", 400

        return jsonify(msg=msg), code

    @app.post("/api/resetPassword")
    def resetPassword():
        newPassword = request.form['newPassword']

        msg, code = "", 0
        if not is_valid_password(newPassword): 
            msg, code = "password invalid. The password needs to have at least one lowercase letter, uppercase letter, number, special character and at least 12 characters in total", 400
        elif(token := request.args.get("token", type=str)):
            msg, code = reset_user_password(token, newPassword)
        else: msg, code = "You need a token to reset a users password", 400
        return jsonify(msg=msg), code


    @app.get("/api/userinfo")
    @jwt_required()
    def userinfo():
        user: User = current_user
        if (email := request.args.get("email", type=str)):
            if not user.is_admin:
                logger.info(
                    f"Non-admin tried to access user info of {email}, denied")
                return jsonify(msg="You don't have permission to view other accounts' user info"), 403
            logger.info(f"Admin requested user info for {user.email}")
            user = User.query.where(User.email == email).one_or_none()
            if not user:
                logger.info(" -> Invalid user email")
                return jsonify(msg="No user exists with that email"), 400
        else:
            logger.info(f"Requested user info for {user.email}")
        return jsonify(email=user.email, isAdmin=user.is_admin, activated=user.activated)

    @app.post("/api/deleteUser")
    @jwt_required()
    def deleteUser():
        thisUser: User = current_user
        toDelete: User = current_user

        # ask for password as confirmation
        password = request.form['password']
        if not thisUser.check_password(password):
            logger.info(" -> incorrect password")
            return jsonify(msg="Incorrect password provided"), 403

        if 'emailDelete' in request.form:
            specifiedEmail = request.form['emailDelete']
            specifiedUser = User.query.where(
                User.email == specifiedEmail).one_or_none()
            if not thisUser.is_admin:
                logger.info(
                    f"Non-admin tried to delete user {specifiedEmail}, denied")
                return jsonify(msg="You don't have permission to delete other users"), 403
            elif not specifiedUser:
                logger.info(" -> Invalid user email")
                return jsonify(msg="No user exists with that email"), 400
            else:
                toDelete = specifiedUser

        logger.info(f"user deletion request from {thisUser.email} for user {toDelete.email}")
        message, code = delete_user(toDelete)
        return jsonify(msg=message), code

    @app.post("/api/changeUserPassword")
    @jwt_required()
    def changeUserPassword():
        thisUser: User = current_user
        toModify: User = current_user

        # ask for password as confirmation
        password = request.form['password']
        if not thisUser.check_password(password):
            logger.info(" -> incorrect password")
            return jsonify(msg="Incorrect password provided"), 403

        if 'emailModify' in request.form:
            specifiedEmail = request.form['emailModify']
            specifiedUser = User.query.where(
                User.email == specifiedEmail).one_or_none()
            if not thisUser.is_admin:
                logger.info(
                    f"Non-admin tried to modify password of user {specifiedEmail}, denied")
                return jsonify(msg="You don't have permission to modify other users"), 403
            elif not specifiedUser:
                logger.info(" -> Invalid user email")
                return jsonify(msg="No user exists with that email"), 400
            else:
                toModify = specifiedUser

        newPassword = request.form['newPassword']
        if not is_valid_password(password): 
            return jsonify(msg="password invalid. The password needs to have at least one lowercase letter, uppercase letter, number, special character and at least 12 characters in total"), 400

        logger.info(f"request to modify user password from {thisUser.email} for user {toModify.email}")
        toModify.set_password_unchecked(newPassword)
        return jsonify(msg="Successfully updated user password"), 200

    @app.post("/api/changeUserEmail")
    @jwt_required()
    def changeUserEmail():
        thisUser: User = current_user
        toModify: User = current_user

        # ask for password as confirmation
        password = request.form['password']
        if not thisUser.check_password(password):
            logger.info(" -> incorrect password")
            return jsonify(msg="Incorrect password provided"), 403

        if 'emailModify' in request.form:
            specifiedEmail = request.form['emailModify']
            specifiedUser = User.query.where(
                User.email == specifiedEmail).one_or_none()
            if not thisUser.is_admin:
                logger.info(
                    f"Non-admin tried to modify users {specifiedEmail} email, denied")
                return jsonify(msg="You don't have permission to modify other users"), 403
            elif not specifiedUser:
                logger.info(" -> Invalid user email")
                return jsonify(msg="No user exists with that email"), 400
            else:
                toModify = specifiedUser

        newEmail = request.form['newEmail']
        if not is_valid_email(newEmail): 
            return jsonify(msg=f"'{newEmail}' is not a valid email address", allowedEmailDomains=app.config["loginSecurity"]["allowedEmailDomains"]), 400

        logger.info(f"request to modify user email from {thisUser.email} to {toModify.email}")
        if send_activation_email(toModify.email, newEmail): 
            return jsonify(msg="Successfully requested email address change. Please confirm your new address by clicking on the link provided in the email we just sent you"), 200
        else:
            return jsonify(msg=f"Failed to send activation email to {newEmail}. Email address may not exist"), 400

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
        runner_manager.enqueue_job(job)
        return jsonify(jobId=job.id)

    @app.get("/api/jobs/list")
    @jwt_required()
    def listJobs():
        user: User = current_user
        requested_user = user
        if "email" in request.args or "all" in request.args:
            if not user.is_admin:
                logger.info("Non-admin tried to list other users' jobs, denied")
                return jsonify(msg="You don't have permission to list other users' jobs"), 403

            if request.args.get("all", type=bool):
                ids_by_user = list_job_ids_for_all_users()
                return jsonify([{"userId": user_id, "jobIds": job_ids}
                                for (user_id, job_ids) in ids_by_user.items()]), 200

            email = request.args["email"]
            requested_user = User.query.where(User.email == email).one_or_none()
            if not requested_user:
                logger.info(f"Admin tried to list jobs of nonexistent user {email}")
                return jsonify(msg="No user exists with that email"), 400

        return jsonify(jobIds=list_job_ids_for_user(requested_user)), 200

    @app.post("/api/jobs/info")
    @jwt_required()
    def jobInfo():
        user: User = current_user
        try:
            job_ids = [int(job_id) for job_id in request.form["jobIds"].split(",")]
        except ValueError:
            return jsonify(msg="`jobIds` must be comma-separated list of integers"), 400
        result = []
        for job_id in job_ids:
            job: Job = Job.query.where(Job.id == job_id).one_or_none()
            # Technically, job IDs aren't secret, so leaking whether they exist
            # isn't a big deal, but it still seems cleaner this way
            if not job:
                if user.is_admin:
                    return jsonify(msg=f"There exists no job with id {job_id}"), 404
                return jsonify(msg=f"You don't have permission to access the job with id {job_id}"), 403
            if job.user_id != user.id and not user.is_admin:
                return jsonify(msg=f"You don't have permission to access the job with id {job_id}"), 403
            result.append({
                "jobId": job.id,
                "fileName": job.file.file_name,
                "model": job.model,
                "language": job.language,
                "status": runner_manager.status_dict(job)
            })
        return jsonify(result)

    @app.get("/api/runners/create")
    @jwt_required()
    def createRunner():
        user: User = current_user
        if not user.is_admin:
            logger.info(f"non-admin ({user.email}) tried to create runner.")
            return jsonify(msg="Only admins may create runner tokens.")
        token, _ = create_runner()
        logger.info(f"Admin {user.email} created runner with token {token}")
        return jsonify(runnerToken=token)

    @app.post("/api/runners/register")
    def registerRunner():
        token, error = auth_token_from_req(request)
        if error:
            return jsonify(error=error), 400
        runner = get_runner_by_token(token)
        if runner is None:
            return jsonify(error="No runner with that token exists!"), 400
        if runner_manager.register_runner(runner):
            logger.info(f"Runner {runner.id} successfully registered!")
            return jsonify(msg="Runner successfully registered!")
        return jsonify(error="Runner is already registered!"), 400

    @app.post("/api/runners/unregister")
    def unregisterRunner():
        runner, error = runner_manager.get_online_runner_for_req(request)
        if error:
            return jsonify(error=error), 400
        if runner_manager.unregister_runner(runner):
            logger.info(f"Runner {runner.runner.id} successfully unregistered!")
            return jsonify(msg="Runner successfully unregistered!")
        return jsonify(error="Runner is not registered!"), 400

    @app.post("/api/runners/retrieveJob")
    def retrieveJob():
        online_runner, error = runner_manager.get_online_runner_for_req(request)
        if error:
            return jsonify(error=error), 400
        job = runner_manager.retrieve_job(online_runner)
        if not job:
            return jsonify(error="No job available!"), 400
        return jsonify(audio=base64.b64encode(job.file.audio_data).decode("ascii"), model=job.model, language=job.language)

    @app.post("/api/runners/submitJobResult")
    def submitJobResult():
        online_runner, error = runner_manager.get_online_runner_for_req(request)
        if error:
            return jsonify(error=error), 400

        if (error_msg := request.form.get("error_msg")):
            runner_manager.submit_job_result(online_runner, error_msg, True)
            return jsonify(msg="Successfully submitted failed job!")

        runner_manager.submit_job_result(online_runner, request.form["transcript"], False)
        return jsonify(msg="Transcript successfully submitted!")

    @app.post("/api/runners/heartbeat")
    def heartbeat():
        token, error = auth_token_from_req(request)
        if error:
            return jsonify(error=error), 400
        runner = get_runner_by_token(token)
        return runner_manager.heartbeat(runner, request).jsonify()

    with app.app_context():
        db.create_all()
        runner_manager.load_jobs_from_db()

    return app
