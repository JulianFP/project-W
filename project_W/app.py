import base64
import datetime
import secrets
from typing import Optional
from pathlib import Path
from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, create_access_token, current_user, jwt_required
from project_W.utils import auth_token_from_req
from flask_cors import CORS
from .logger import get_logger
from .model import Job, User, activatedRequired, add_new_user, create_runner, delete_user, \
    get_runner_by_token, list_job_ids_for_all_users, list_job_ids_for_user, \
    submit_job, db, activate_user, send_activation_email, send_password_reset_email, \
    reset_user_password, is_valid_email, is_valid_password, confirmIdentity, emailModifyForAdmins
from .config import loadConfig
from .runner_manager import RunnerManager


def create_app(customConfigPath: Optional[str] = None) -> Flask:
    logger = get_logger("project-W")
    app = Flask("project-W")
    CORS(app)

    # load config from additionalPaths (if not None) + defaultSearchDirs
    if customConfigPath is None:
        app.config.update(loadConfig())
    else:
        path = Path(customConfigPath)
        if not path.is_dir():
            path = path.parent
        app.config.update(loadConfig(additionalPaths=[path]))

    # check syntax of JWT_SECRET_KEY and update if necessary
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
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = datetime.timedelta(
        minutes=app.config["loginSecurity"]["sessionExpirationTimeMinutes"])
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

    @app.post("/api/users/signup")
    def signup():
        """
        Create a new user account by setting its email and password. The following conditions have to be met for this to succeed:

        - Signup of new accounts can't be disabled on this server. Refer to :ref:`description_backend_config-label`. ErrorType: ``serverConfig``.
        - Provided email has to have the format of an email address (`something`@`(sub)domain`.`tld`) and its `(sub)domain` needs to be on the allow-list of the server. Refer to :ref:`description_backend_config-label`. ErrorType: ``email``.
        - Provided password has be at least 12 characters long and has to include at least one lower case letter, upper case letter, digit and special character. ErrorType: ``password``.
        - The email can't be already in use by another account. ErrorType: ``email``.
        - Sending a confirmation mail to the email address has to succeed. ErrorType: ``email``.

        .. :quickref: Users; Create a new user account.

        :form email: Email address of new user
        :form password: Password of new user
        :resjson string msg: Human-readable response message designed to be directly shown to users
        :resjson string errorType: One of ``serverConfig``, ``email``, ``password`` for this route. Refer to :ref:`error_types-label`
        :resjson string[] allowedEmailDomains: Exists only if msg=="'{email}' is not a valid email address". List of allowed email domains on this server. Can be empty which means that all domains are allowed. You probably want to show this to your users.
        :status 200: User successfully created. Email confirmation mail successfully sent.
        :status 400: User not created, no confirmation mail was sent. Refer to `errorType` and `msg` for what went wrong.
        """
        if app.config["loginSecurity"]["disableSignup"]:
            return jsonify(msg="Signup of new accounts is disabled on this server", errorType="serverConfig"), 400

        email = request.form['email']
        password = request.form['password']
        logger.info(f"Signup request from {email}")

        if not is_valid_email(email):
            return jsonify(msg=f"'{email}' is not a valid email address", errorType="email", allowedEmailDomains=app.config["loginSecurity"]["allowedEmailDomains"]), 400
        if not is_valid_password(password):
            return jsonify(msg="Password invalid. The password needs to have at least one lowercase letter, uppercase letter, number, special character and at least 12 characters in total", errorType="password"), 400

        return add_new_user(email, password, False)

    @app.post("/api/users/activate")
    def activate():
        """
        Activate an user account by clicking on the link in the confirmation mail. The user will get the link with the token for this per email. The following conditions have to be met for this to succeed:
        
        - The provided Token has to be valid and decoding it has to succeed. ErrorType: ``auth``.
        - An account with the email address that was encoded into the token has to exist. ErrorType: ``notInDatabase``. 
        - The account can't already be activated. ErrorType: ``operation``.

        .. :quickref: Users; Activate an user account by confirming email address.

        :form token: Activation token (delivered by email)
        :resjson string msg: Human-readable response message designed to be directly shown to users
        :resjson string errorType: One of ``auth``, ``notInDatabase``, ``operation`` for this route. Refer to :ref:`error_types-label`
        :status 200: User successfully activated.
        :status 400: User not activated. Refer to `errorType` and `msg` for what went wrong.
        """
        if (token := request.form.get("token", type=str)):
            return activate_user(token)
        else:
            return jsonify(msg="You need a token to activate a users email", errorType="auth"), 400

    @app.post("/api/users/login")
    def login():
        """
        Log in into an user account. This will return a JWT Token that needs to be used for authentication in routes that require it. The following conditions have to be met for this to succeed:
        
        - An account with the provided email address has to exist. ErrorType: ``auth``.
        - The provided password has to match the accounts password. ErrorType: ``auth``.

        .. :quickref: Users; Log in into an user account.

        :form email: Email address of user
        :form password: Password of user account associated with `email`
        :resjson string msg: Human-readable response message designed to be directly shown to users
        :resjson string errorType: ``auth`` for this route. Refer to :ref:`error_types-label`
        :resjson string accessToken: JWT Token
        :status 200: Successfully logged in.
        :status 400: Login not successful. Refer to `errorType` and `msg` for what went wrong.
        """
        email = request.form['email']
        password = request.form['password']
        logger.info(f"Login request from {email}")

        user: Optional[User] = User.query.where(
            User.email == email).one_or_none()

        if not (user and user.check_password(password)):
            logger.info(" -> incorrect credentials")
            return jsonify(msg="Incorrect credentials provided", errorType="auth"), 400

        logger.info(" -> login successful, returning JWT token")
        return jsonify(msg="Login successful", accessToken=create_access_token(user))

    @app.get("/api/users/requestPasswordReset")
    def requestPasswordReset():
        """
        Request a password reset email for a user account. The following conditions have to be met for this to succeed:
        
        - An account with the provided email address has to exist (if this condition doesn't hold, then no mail will be sent but the route still returns status 200). ErrorType: ``email``.
        - Sending the email has to succeed. ErrorType: ``email``.

        .. :quickref: Users; Request password reset email

        :qparam email: Email address of user
        :resjson string msg: Human-readable response message designed to be directly shown to users
        :resjson string errorType: ``email`` for this route. Refer to :ref:`error_types-label`
        :status 200: If account with `email` exists, then the mail was successfully sent. Else nothing.
        :status 400: Error when trying to sent email.
        """
        email = request.args['email']
        logger.info(f"Password reset request for email {email}")

        user: Optional[User] = User.query.where(
            User.email == email).one_or_none()
        if user is None:
            # do not change the output in this case since that would allow anybody to probe for emails which have an account here
            logger.info(
                f"  -> password reset request for unknown email address '{email}'")
        elif not send_password_reset_email(email):
            return jsonify(msg=f"Failed to send password reset email to {email}.", errorType="email"), 400

        return jsonify(msg=f"If an account with the address {email} exists, then we sent a password reset email to this address. Please check your emails"), 200

    @app.post("/api/users/resetPassword")
    def resetPassword():
        """
        Reset a users password after getting the password reset email. The following conditions have to be met for this to succeed:
        
        - Provided new password has be at least 12 characters long and has to include at least one lower case letter, upper case letter, digit and special character. ErrorType: ``password``.
        - The provided Token has to be valid and decoding it has to succeed. ErrorType: ``auth``.
        - An account with the email address that was encoded into the token has to exist. ErrorType: ``notInDatabase``. 

        .. :quickref: Users; Reset user password with Token from email.

        :form token: Password reset token (delivered by email)
        :form newPassword: new password that should be set for this account
        :resjson string msg: Human-readable response message designed to be directly shown to users
        :resjson string errorType: One of ``password``, ``auth``, ``notInDatabase`` for this route. Refer to :ref:`error_types-label`
        :status 200: Password successfully changed.
        :status 400: Password not changed. Refer to `errorType` and `msg` for what went wrong.
        """
        newPassword = request.form['newPassword']

        if not is_valid_password(newPassword):
            return jsonify(msg="Password invalid. The password needs to have at least one lowercase letter, uppercase letter, number, special character and at least 12 characters in total", errorType="password"), 400
        elif (token := request.form.get("token", type=str)):
            return reset_user_password(token, newPassword)
        else:
            return jsonify(msg="You need a token to reset a users password", errorType="auth"), 400

    @app.get("/api/users/info")
    @jwt_required()
    def userinfo():
        """
        Get the account information of the currently logged in account. If you are currently logged in with an admin account you can also get account information of another user account with provided email. The following conditions have to be met for this to succeed:
        
        - Correct and valid JWT Token has to be supplied in Authorization header. No errorType field.
        - If trying to access other users info (e.g. if `email` is not empty): Currently logged in account has to be admin. ErrorType: ``permission``.
        - If trying to access other users info (e.g. if `email` is not empty): An account with the provided email address has to exist. ErrorType: ``notInDatabase``.

        .. :quickref: Users; Get account information of an user account

        :reqheader Authorization: Has to be string "Bearer {JWT}", where {JWT} is the JWT Token that the login route returned.
        :qparam email (optional): Email of account that you want to access (leave empty if you want to access own account)
        :resjson string msg: Human-readable response message designed to be directly shown to users
        :resjson string errorType: One of ``permission``, ``notInDatabase`` for this route. Refer to :ref:`error_types-label`
        :resjson string email: Email address of the account
        :resjson bool isAdmin: Whether the account is an admin account
        :resjson bool activated: Whether the account is activated

        :status 200: Returns account information.
        :status 400: With errorType ``notInDatabase``.
        :status 403: With errorType ``permission``.
        """
        user: User = current_user
        if (email := request.args.get("email", type=str)):
            if not user.is_admin:
                logger.info(
                    f"Non-admin tried to access user info of {email}, denied")
                return jsonify(msg="You don't have permission to view other accounts' user info", errorType="permission"), 403
            logger.info(f"Admin requested user info for {user.email}")
            user = User.query.where(User.email == email).one_or_none()
            if not user:
                logger.info(" -> Invalid user email")
                return jsonify(msg="No user exists with that email", errorType="notInDatabase"), 400
        else:
            logger.info(f"Requested user info for {user.email}")
        return jsonify(email=user.email, isAdmin=user.is_admin, activated=user.activated)

    @app.post("/api/users/delete")
    @jwt_required()
    @confirmIdentity
    @emailModifyForAdmins
    def deleteUser(toModify: User):
        """
        Delete the currently logged in account with all information associated with it. If you are currently logged in with an admin account you can also delete another user account with provided email. The following conditions have to be met for this to succeed:
        
        - Correct and valid JWT Token has to be supplied in Authorization header. No errorType field.
        - The provided password has to match the accounts password. ErrorType: ``auth``.
        - If trying to delete other users account (e.g. if `emailModify` is not empty): Currently logged in account has to be admin. ErrorType: ``permission``.
        - If trying to delete other users account (e.g. if `emailModify` is not empty): An account with the provided email address has to exist. ErrorType: ``notInDatabase``.

        .. :quickref: Users; Delete an user account

        :reqheader Authorization: Has to be string "Bearer {JWT}", where {JWT} is the JWT Token that the login route returned.
        :form password: Password of user account associated with the currently logged in account/`emailModify`
        :form emailModify (optional): Email of account that you want to access (leave empty if you want to access own account)
        :resjson string msg: Human-readable response message designed to be directly shown to users
        :resjson string errorType: One of ``auth``, ``permission``, ``notInDatabase`` for this route. Refer to :ref:`error_types-label`

        :status 200: User account gets deleted.
        :status 400: With errorType ``notInDatabase``.
        :status 403: With errorTypes ``permission`` and ``auth``.
        """
        thisUser: User = current_user

        logger.info(
            f"user {thisUser.email} made request to delete user {toModify.email}")

        return delete_user(toModify)

    @app.post("/api/users/changePassword")
    @jwt_required()
    @confirmIdentity
    @emailModifyForAdmins
    def changeUserPassword(toModify: User):
        """
        Change the password of the currently logged in account. If you are currently logged in with an admin account you can also change the password of another user account with provided email. The following conditions have to be met for this to succeed:
        
        - Correct and valid JWT Token has to be supplied in Authorization header. No errorType field.
        - The provided password has to match the accounts password. ErrorType: ``auth``.
        - If trying to delete other users account (e.g. if `emailModify` is not empty): Currently logged in account has to be admin. ErrorType: ``permission``.
        - If trying to delete other users account (e.g. if `emailModify` is not empty): An account with the provided email address has to exist. ErrorType: ``notInDatabase``.
        - Provided new password has be at least 12 characters long and has to include at least one lower case letter, upper case letter, digit and special character. ErrorType: ``password``.

        .. :quickref: Users; Change password of an user account

        :reqheader Authorization: Has to be string "Bearer {JWT}", where {JWT} is the JWT Token that the login route returned.
        :form password: Password of user account associated with the currently logged in account/`emailModify`
        :form newPassword: new password that should be set for this account
        :form emailModify (optional): Email of account that you want to access (leave empty if you want to access own account)
        :resjson string msg: Human-readable response message designed to be directly shown to users
        :resjson string errorType: One of ``auth``, ``permission``, ``notInDatabase``, ``password`` for this route. Refer to :ref:`error_types-label`

        :status 200: Password change successful.
        :status 400: With errorType ``notInDatabase`` and ``password``.
        :status 403: With errorTypes ``permission`` and ``auth``.
        """
        thisUser: User = current_user
        newPassword = request.form['newPassword']

        if not is_valid_password(newPassword):
            return jsonify(msg="Password invalid. The password needs to have at least one lowercase letter, uppercase letter, number, special character and at least 12 characters in total", errorType="password"), 400

        logger.info(
            f"user {thisUser.email} made request to modify user password of user {toModify.email}")

        toModify.set_password_unchecked(newPassword)
        return jsonify(msg="Successfully updated user password"), 200

    @app.post("/api/users/changeEmail")
    @jwt_required()
    @confirmIdentity
    @emailModifyForAdmins
    def changeUserEmail(toModify: User):
        """
        Change the email address of the currently logged in account. If you are currently logged in with an admin account you can also change the email address of another user account with provided email. The following conditions have to be met for this to succeed:
        
        - Correct and valid JWT Token has to be supplied in Authorization header. No errorType field.
        - The provided password has to match the accounts password. ErrorType: ``auth``.
        - If trying to delete other users account (e.g. if `emailModify` is not empty): Currently logged in account has to be admin. ErrorType: ``permission``.
        - If trying to delete other users account (e.g. if `emailModify` is not empty): An account with the provided email address has to exist. ErrorType: ``notInDatabase``.
        - Provided new email has to have the format of an email address (`something`@`(sub)domain`.`tld`) and its `(sub)domain` needs to be on the allow-list of the server. Refer to :ref:`description_backend_config-label`. ErrorType: ``email``.
        - The new email can't be already in use by another account. ErrorType: ``email``.
        - Sending a confirmation mail to the new email address has to succeed. ErrorType: ``email``.

        .. :quickref: Users; Change email address of an user account

        :reqheader Authorization: Has to be string "Bearer {JWT}", where {JWT} is the JWT Token that the login route returned.
        :form password: Password of user account associated with the currently logged in account/`emailModify`
        :form newEmail: New email address that should be set for the user
        :form emailModify (optional): Email of account that you want to access (leave empty if you want to access own account)
        :resjson string msg: Human-readable response message designed to be directly shown to users
        :resjson string errorType: One of ``auth``, ``permission``, ``notInDatabase``, ``email`` for this route. Refer to :ref:`error_types-label`
        :resjson string[] allowedEmailDomains: Exists only if msg=="'{email}' is not a valid email address". List of allowed email domains on this server. Can be empty which means that all domains are allowed. You probably want to show this to your users.

        :status 200: Email changed successfully. Confirmation mail was sent successfully.
        :status 400: With errorType ``notInDatabase`` and ``email``.
        :status 403: With errorTypes ``permission`` and ``auth``.
        """
        thisUser: User = current_user
        newEmail = request.form['newEmail']

        if not is_valid_email(newEmail):
            return jsonify(msg=f"'{newEmail}' is not a valid email address", errorType="email", allowedEmailDomains=app.config["loginSecurity"]["allowedEmailDomains"]), 400
        emailInUse: bool = db.session.query(
            User.query.where(User.email == newEmail).exists()).scalar()
        if emailInUse:
            return jsonify(msg="E-Mail is already used by another account", errorType="email"), 400

        logger.info(
            f"user {thisUser.email} made request to modify user email of user {toModify.email} to {newEmail}")

        if send_activation_email(toModify.email, newEmail):
            return jsonify(msg="Successfully requested email address change. Please confirm your new address by clicking on the link provided in the email we just sent you"), 200
        else:
            return jsonify(msg=f"Failed to send activation email to {newEmail}. Email address may not exist", errorType="email"), 400

    @app.get("/api/users/resendActivationEmail")
    @jwt_required()
    def resendActivationEmail():
        """
        Resend the confirmation email for the currently logged in account. The following conditions have to be met for this to succeed:
        
        - Correct and valid JWT Token has to be supplied in Authorization header. No errorType field.
        - The account can't already be activated. ErrorType: ``operation``.
        - Sending a confirmation mail to the email address has to succeed. ErrorType: ``email``.

        .. :quickref: Users; Resend confirmation email

        :reqheader Authorization: Has to be string "Bearer {JWT}", where {JWT} is the JWT Token that the login route returned.
        :resjson string msg: Human-readable response message designed to be directly shown to users
        :resjson string errorType: One of ``operation``, ``email`` for this route. Refer to :ref:`error_types-label`

        :status 200: Confirmation email was sent successfully.
        :status 400: Nothing happens.
        """
        user: User = current_user
        if user.activated:
            return jsonify(msg="This user is already activated", errorType="operation"), 400

        if not send_activation_email(user.email, user.email):
            return jsonify(msg=f"Failed to send password reset email to {user.email}.", errorType="email"), 400

        return jsonify(msg=f"We have sent a new password reset email to {user.email}. Please check your emails"), 200

    @app.post("/api/users/invalidateAllTokens")
    @jwt_required()
    def invalidateAllTokens():
        """
        Invalidate all JWT Tokens for the currently logged in account. This means that all browser/client sessions will be revoked and the user has to log in using their email and password again. The following conditions have to be met for this to succeed:
        
        - Correct and valid JWT Token has to be supplied in Authorization header. No errorType field.

        .. :quickref: Users; Revoke all user sessions

        :reqheader Authorization: Has to be string "Bearer {JWT}", where {JWT} is the JWT Token that the login route returned.
        :resjson string msg: Human-readable response message designed to be directly shown to users

        :status 200: All Tokens were invalidated successfully.
        """
        user: User = current_user
        user.invalidate_session_tokens()

        return jsonify(msg="You have successfully been logged out accross all your devices"), 200

    @app.post("/api/jobs/submit")
    @jwt_required()
    @activatedRequired
    def submitJob():
        """
        Submit a new transcription job by posting the file as well as some job details. The backend will create a new job, immediately assign it to a free runner (if one exists) and return its jobID. The following conditions have to be met for this to succeed:
        
        - Correct and valid JWT Token has to be supplied in Authorization header. No errorType field.
        - The user to which the JWT Token belongs has to be activated (i.e. has to have confirmed their email address). ErrorType: ``permission``.

        .. :quickref: Jobs; Submit a new job

        :reqheader Authorization: Has to be string "Bearer {JWT}", where {JWT} is the JWT Token that the login route returned.
        :form file: Audio data that should be transcribed as a binary file
        :form model (optional): Whisper model that should be used. One of: [ tiny, tiny.en, base, base.en, small, small.en, medium, medium.en, large ]. Defaults to: `small`.
        :form language (optional): Language to transcribe to (spoken language in audio file). One of: [ af, am, ar, as, az, ba, be, bg, bn, bo, br, bs, ca, cs, cy, da, de, el, en, es, et, eu, fa, fi, fo, fr, gl, gu, ha, haw, he, hi, hr, ht, hu, hy, id, is, it, ja, jw, ka, kk, km, kn, ko, la, lb, ln, lo, lt, lv, mg, mi, mk, ml, mn, mr, ms, mt, my, ne, nl, nn, no, oc, pa, pl, ps, pt, ro, ru, sa, sd, si, sk, sl, sn, so, sq, sr, su, sv, sw, ta, te, tg, th, tk, tl, tr, tt, uk, ur, uz, vi, yi, yo, yue, zh ] or the same languages but written out (first letter in uppercase), e.g. `English` or `German`. If left away then whisper will detect the language automatically.
        :resjson string msg: Human-readable response message designed to be directly shown to users
        :resjson string errorType: ``permission`` for this route. Refer to :ref:`error_types-label`
        :resjson integer jobId: ID of the newly created job.

        :status 200: A new job with the submitted details was created successfully.
        :status 403: With errorType ``permission``.
        """
        user: User = current_user
        file = request.files["file"]
        file.stream.seek(0)
        file_name = file.filename
        audio = file.stream.read()
        model = request.form.get("model")
        language = request.form.get("language")
        job = submit_job(user, file_name, audio, model, language)
        runner_manager.enqueue_job(job)
        return jsonify(msg="Job successfully submitted", jobId=job.id)

    @app.get("/api/jobs/list")
    @jwt_required()
    def listJobs():
        """
        Get a list of all jobs either of this user account or of another user account/all users (only possible if you are admin). Returns all jobs as a list of job ids. The following conditions have to be met for this to succeed:
        
        - Correct and valid JWT Token has to be supplied in Authorization header. No errorType field.
        - If trying to list jobs of other users accounts (e.g. if `email` or `all` is not empty): Currently logged in account has to be admin. ErrorType: ``permission``.
        - If trying to list all jobs of another user (e.g. if `email` is not empty): An account with the provided email address has to exist. ErrorType: ``notInDatabase``.

        .. :quickref: Jobs; List all job-IDs associated with an user account

        :reqheader Authorization: Has to be string "Bearer {JWT}", where {JWT} is the JWT Token that the login route returned.
        :qparam all (optional): Set to `1` if you want to get all jobs of all accounts.
        :qparam email (optional): Email address of account of which you want to get all jobs from (leave empty to access all jobs of your own account).
        :resjson string msg: Human-readable response message designed to be directly shown to users
        :resjson string errorType: One of ``permission``, ``notInDatabase`` for this route. Refer to :ref:`error_types-label`
        :resjson list_of_integers jobIds: JobIds of all requested jobs.

        :status 200: A new job with the submitted details was created successfully.
        :status 400: With errorType ``notInDatabase``.
        :status 403: With errorType ``permission``.
        """
        user: User = current_user
        requested_user = user
        if "email" in request.args or "all" in request.args:
            if not user.is_admin:
                logger.info(
                    "Non-admin tried to list other users' jobs, denied")
                return jsonify(msg="You don't have permission to list other users' jobs", errorType="permission"), 403

            if request.args.get("all", type=bool):
                ids_by_user = list_job_ids_for_all_users()
                return jsonify(msg="Returning all list of all jobs in database", jobs=[{"userId": user_id, "jobIds": job_ids}
                                for (user_id, job_ids) in ids_by_user.items()]), 200

            email = request.args["email"]
            requested_user = User.query.where(
                User.email == email).one_or_none()
            if not requested_user:
                logger.info(
                    f"Admin tried to list jobs of nonexistent user {email}")
                return jsonify(msg="No user exists with that email", errorType="notInDatabase"), 400

        return jsonify(msg="Returning list of all jobs of your account", jobIds=list_job_ids_for_user(requested_user)), 200

    @app.get("/api/jobs/info")
    @jwt_required()
    def jobInfo():
        """
        Get all information related to the given jobs. This contains stuff like the filename, the used model or the current status and progress. By giving a list of jobIds you can access the information of multiple jobs with just one request. The following conditions have to be met for this to succeed:
        
        - Correct and valid JWT Token has to be supplied in Authorization header. No errorType field.
        - `jobIds` has to have the correct format as described below. ErrorType: ``invalidRequest``
        - If trying to access job of another user (e.g. if one of `jobIds` doesn't belong to this user): Currently logged in account has to be admin. ErrorType: ``permission``.
        - If trying to access job of another user (e.g. if one of `jobIds` doesn't belong to this user): A job with the provided jobId has to exist. ErrorType: ``notInDatabase``.

        .. :quickref: Jobs; Get detailed information to all provided jobIds

        :reqheader Authorization: Has to be string "Bearer {JWT}", where {JWT} is the JWT Token that the login route returned.
        :qparam jobIds: List of Job-IDs as a string, separated by commas, e.g. `2,4,5,6`.
        :resjson string msg: Human-readable response message designed to be directly shown to users
        :resjson string errorType: One of ``permission``, ``notInDatabase`` for this route. Refer to :ref:`error_types-label`
        :resjson list_of_objects jobs: Info of all requested jobs. Each object can (but doesn't have to) contain the following fields: `jobId: integer`, `fileName: string`, `model: string`, `language: string`, `status: object that can contain the fields 'step: string', 'runner: integer', 'progress: float'`.

        :status 200: Returning the requested job infos.
        :status 400: With errorType ``invalidRequest``.
        :status 403: With errorType ``permission``.
        :status 404: With errorType ``notInDatabase``.
        """
        user: User = current_user
        try:
            job_ids = [int(job_id)
                       for job_id in request.args["jobIds"].split(",")]
        except ValueError:
            return jsonify(msg="`jobIds` must be comma-separated list of integers", errorType="invalidRequest"), 400
        result = []
        for job_id in job_ids:
            job: Job = Job.query.where(Job.id == job_id).one_or_none()
            # Technically, job IDs aren't secret, so leaking whether they exist
            # isn't a big deal, but it still seems cleaner this way
            if not job:
                if user.is_admin:
                    return jsonify(msg=f"There exists no job with id {job_id}", errorType="notInDatabase"), 404
                return jsonify(msg=f"You don't have permission to access the job with id {job_id}", errorType="permission"), 403
            if job.user_id != user.id and not user.is_admin:
                return jsonify(msg=f"You don't have permission to access the job with id {job_id}", errorType="permission"), 403
            result.append({
                "jobId": job.id,
                "fileName": job.file_name,
                "model": job.model,
                "language": job.language,
                "status": runner_manager.status_dict(job)
            })
        return jsonify(msg="Returning requested jobs", jobs=result)

    @app.get("/api/jobs/downloadTranscript")
    @jwt_required()
    def downloadTranscript():
        """
        Download the transcript of a successfully completed job in the form of a long String. The following conditions have to be met for this to succeed:
        
        - Correct and valid JWT Token has to be supplied in Authorization header. No errorType field.
        - A job with the provided jobId has to exist. ErrorType: ``notInDatabase``.
        - If trying to access job of another user (e.g. if one of `jobIds` doesn't belong to this user): Currently logged in account has to be admin. ErrorType: ``permission``.
        - The job with the provided jobId has to have a transcript as an attribute (meaning it needs to have finished without an error). ErrorType: ``operation``

        .. :quickref: Jobs; Download transcript of a finished job.

        :reqheader Authorization: Has to be string "Bearer {JWT}", where {JWT} is the JWT Token that the login route returned.
        :qparam jobId: Job-ID of the job of which to download the transcript from.
        :resjson string msg: Human-readable response message designed to be directly shown to users
        :resjson string errorType: One of ``notInDatabase``, ``permission``, ``operation`` for this route. Refer to :ref:`error_types-label`
        :resjson string transcript: Finished transcript. You may want to store this as a file.

        :status 200: Returning the requested transcript.
        :status 400: With errorType ``operation``.
        :status 403: With errorType ``permission``.
        :status 404: With errorType ``notInDatabase``.
        """
        user: User = current_user
        job_id = request.args["jobId"]
        job: Job = Job.query.where(Job.id == job_id).one_or_none()
        if not job:
            return jsonify(msg=f"There exists no job with id {job_id}", errorType="notInDatabase"), 404
        if job.user_id != user.id and not user.is_admin:
            return jsonify(msg="You don't have permission to access this job", errorType="permission"), 403

        if job.transcript is not None:
            job.downloaded = True
            db.session.commit()
            return jsonify(msg="Returning transcript of job {job_id}", transcript=job.transcript)
        elif job.error_msg is not None:
            return jsonify(msg=job.error_msg, errorType="operation"), 404
        return jsonify(msg="Job isn't done yet", errorType="operation"), 404

    @app.get("/api/runners/create")
    @jwt_required()
    def createRunner():
        """
        Create a new runner and get its runner Token. You need to call this route before you can configure and start you Runner. The following conditions have to be met for this to succeed:
        
        - Correct and valid JWT Token (of a user) has to be supplied in Authorization header.
        - The user associated with that JWT Token has to be an admin.

        .. :quickref: Runners; Create a new runner and get its token.

        :reqheader Authorization: Has to be string "Bearer {JWT}", where {JWT} is the JWT Token that the login route returned.
        :resjson string msg: Human-readable error message that tells you why the request failed (for debugging reasons).
        :resjson string runnerToken: Token of the newly created runner.

        :status 200: Runner successfully created and returning its token.
        :status 403: User is not an admin.
        """
        user: User = current_user
        if not user.is_admin:
            logger.info(f"non-admin ({user.email}) tried to create runner.")
            return jsonify(msg="Only admins may create runner tokens."), 403
        token, _ = create_runner()
        logger.info(f"Admin {user.email} created runner with token {token}")
        return jsonify(runnerToken=token), 200

    @app.post("/api/runners/register")
    def registerRunner():
        """
        The runner tells the backend that it is now online and capable of receiving jobs. The following conditions have to be met for this to succeed:
        
        - Correct and valid Runner Token (that is known to the Backend) has to be supplied in Authorization header.
        - The runner can't already be registered. All runners will be unregistered automatically after 60-70 seconds since the last heartbeat, so if this condition isn't true then just wait a bit.

        .. :quickref: Runners; Runner tells Backend that it is now online.

        :reqheader Authorization: Has to be string "Bearer {Token}", where {Token} is the Runner Token that the /runners/create route returned.
        :resjson string msg: Human-readable success message.
        :resjson string error: Human-readable error message that tells you why the request failed.

        :status 200: Runner successfully registered.
        :status 400: Failed. Refer to ``error`` field for the reason.
        """
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
        """
        The runner tells the backend that it is going offline and can't accept any more jobs. The following conditions have to be met for this to succeed:
        
        - Correct and valid Runner Token (that is known to the Backend) has to be supplied in Authorization header.
        - The runner has to currently be registered. All runners will be unregistered automatically after 60-70 seconds since the last heartbeat.

        .. :quickref: Runners; Runner tells Backend that it is now going offline.

        :reqheader Authorization: Has to be string "Bearer {Token}", where {Token} is the Runner Token that the /runners/create route returned.
        :resjson string msg: Human-readable success message.
        :resjson string error: Human-readable error message that tells you why the request failed.

        :status 200: Runner successfully registered.
        :status 400: Failed. Refer to ``error`` field for the reason.
        """
        runner, error = runner_manager.get_online_runner_for_req(request)
        if error:
            return jsonify(error=error), 400
        if runner_manager.unregister_runner(runner):
            logger.info(
                f"Runner {runner.runner.id} successfully unregistered!")
            return jsonify(msg="Runner successfully unregistered!")
        return jsonify(error="Runner is not registered!"), 400

    @app.post("/api/runners/retrieveJob")
    def retrieveJob():
        """
        The runner retrieves its job after it learned from the heartbeat response that the Backend assigned a job to it. The following conditions have to be met for this to succeed:
        
        - Correct and valid Runner Token (that is known to the Backend) has to be supplied in Authorization header.
        - The runner has to currently be registered. All runners will be unregistered automatically after 60-70 seconds since the last heartbeat.
        - There has to be a job assigned to the runner associated with the given Runner Token.

        .. :quickref: Runners; Runner retrieves the job that got assigned to it.

        :reqheader Authorization: Has to be string "Bearer {Token}", where {Token} is the Runner Token that the /runners/create route returned.
        :resjson string error: Human-readable error message that tells you why the request failed.
        :resjson string audio: Content of audio-file encoded into base64.
        :resjson string model: Whisper model that should be used for the job. May be null.
        :resjson string language: Language of the audio. May be null.

        :status 200: Returning assigned job.
        :status 400: Failed. Refer to ``error`` field for the reason.
        """
        online_runner, error = runner_manager.get_online_runner_for_req(
            request)
        if error:
            return jsonify(error=error), 400
        job = runner_manager.retrieve_job(online_runner)
        if not job:
            return jsonify(error="No job available!"), 400
        return jsonify(audio=base64.b64encode(job.file.audio_data).decode("ascii"), model=job.model, language=job.language)

    @app.post("/api/runners/submitJobResult")
    def submitJobResult():
        """
        The runner submits the result of the finished job by either submitting the transcript or an error message. The following conditions have to be met for this to succeed:
        
        - Correct and valid Runner Token (that is known to the Backend) has to be supplied in Authorization header.
        - The runner has to currently be registered. All runners will be unregistered automatically after 60-70 seconds since the last heartbeat.

        .. :quickref: Runners; Runner submits the result (transcript or error msg) of a finished job.

        :reqheader Authorization: Has to be string "Bearer {Token}", where {Token} is the Runner Token that the /runners/create route returned.
        :form transcript: Text of the finished transcript. The job will get the status `SUCCESS`. Request has to either include this or `error_msg`.
        :form error_msg: Error that occurred during transcribing. The job will get the status `FAILED`. Request has to either include this or `transcript`.
        :resjson string error: Human-readable error message that tells you why the request failed.
        :resjson string msg: Human-readable success message.

        :status 200: Received job result and successfully updated the jobs status.
        :status 400: Failed. Refer to ``error`` field for the reason.
        """
        online_runner, error = runner_manager.get_online_runner_for_req(
            request)
        if error:
            return jsonify(error=error), 400

        if (error_msg := request.form.get("error_msg")):
            runner_manager.submit_job_result(online_runner, error_msg, True)
            return jsonify(msg="Successfully submitted failed job!")

        runner_manager.submit_job_result(
            online_runner, request.form["transcript"], False)
        return jsonify(msg="Transcript successfully submitted!")

    @app.post("/api/runners/heartbeat")
    def heartbeat():
        """
        The runner tells the Backend that it is still online and asks if there is any job assigned to it at the same time. If the Runner is currently working on a job then it tells the Backend the current progress. This route should be called by the runner every 15 seconds. If it isn't called for 60 seconds then the runner may be automatically unregistered by the Backend. The following conditions have to be met for this to succeed:
        
        - Correct and valid Runner Token (that is known to the Backend) has to be supplied in Authorization header.
        - The runner has to currently be registered. All runners will be unregistered automatically after 60-70 seconds since the last heartbeat.

        .. :quickref: Runners; Runner tells backend that it is still online and asks for a job or tells about the progress of the current job.

        :reqheader Authorization: Has to be string "Bearer {Token}", where {Token} is the Runner Token that the /runners/create route returned.
        :form float progress (optional): The progress of the current job as a float between 0 and 1. Will be processed up to a precision of 4 decimal digits (-> so 2 decimal digits if multiplied by 100 for percent representation)
        :resjson string error: Human-readable error message that tells you why the request failed.
        :resjson boolean jobAssigned: If set to `true`, then the Backend has assigned a job to this Runner. `false` or null otherwise. Note that this will also return `true` if the Runner is already processing the job that got assigned to it.

        :status 200: Heartbeat acknowledged. Progress successfully updated.
        :status 400: Failed. Refer to ``error`` field for the reason.
        """
        token, error = auth_token_from_req(request)
        if error:
            return jsonify(error=error), 400
        runner = get_runner_by_token(token)
        return runner_manager.heartbeat(runner, request).jsonify()

    with app.app_context():
        db.create_all()
        runner_manager.load_jobs_from_db()

    return app
