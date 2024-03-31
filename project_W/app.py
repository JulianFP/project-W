import datetime
import secrets
from typing import Optional
from pathlib import Path
from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, create_access_token, current_user, jwt_required
from flask_cors import CORS
from .logger import get_logger
from .model import User, add_new_user, delete_user, db, activate_user, send_activation_email, send_password_reset_email, reset_user_password, is_valid_email, is_valid_password, confirmIdentity, emailModifyForAdmins
from .config import loadConfig

def create_app(customConfigPath: Optional[str] = None) -> Flask:
    logger = get_logger("project-W")
    app = Flask("project-W")
    CORS(app)

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
        if(token := request.form.get("token", type=str)):
            return activate_user(token)
        else: return jsonify(msg="You need a token to activate a users email", errorType="auth"), 400

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
        return jsonify(msg="Login successful", access_token=create_access_token(user))

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
            #do not change the output in this case since that would allow anybody to probe for emails which have an account here
            logger.info(f"  -> password reset request for unknown email address '{email}'")
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
            return jsonify(msg = "Password invalid. The password needs to have at least one lowercase letter, uppercase letter, number, special character and at least 12 characters in total", errorType="password"), 400
        elif(token := request.form.get("token", type=str)):
            return reset_user_password(token, newPassword)
        else: return jsonify(msg="You need a token to reset a users password", errorType="auth"), 400


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
        :qparam email: Email of account that you want to access (leave empty if you want to access own account)
        :resjson string msg: Human-readable response message designed to be directly shown to users
        :resjson string errorType: One of ``permission``, ``notInDatabase`` for this route. Refer to :ref:`error_types-label`
        :resjson string email: Email address of the account
        :resjson bool is_admin: Whether the account is an admin account
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
        return jsonify(email=user.email, is_admin=user.is_admin, activated=user.activated)

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
        :form emailModify: Email of account that you want to access (leave empty if you want to access own account)
        :resjson string msg: Human-readable response message designed to be directly shown to users
        :resjson string errorType: One of ``auth``, ``permission``, ``notInDatabase`` for this route. Refer to :ref:`error_types-label`

        :status 200: User account gets deleted.
        :status 400: With errorType ``notInDatabase``.
        :status 403: With errorTypes ``permission`` and ``auth``.
        """
        thisUser: User = current_user

        logger.info(f"user {thisUser.email} made request to delete user {toModify.email}")

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
        :form emailModify: Email of account that you want to access (leave empty if you want to access own account)
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

        logger.info(f"user {thisUser.email} made request to modify user password of user {toModify.email}")

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
        :form emailModify: Email of account that you want to access (leave empty if you want to access own account)
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

        logger.info(f"user {thisUser.email} made request to modify user email of user {toModify.email} to {newEmail}")

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

    with app.app_context():
        db.create_all()

    return app
