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

    @app.post("/api/signup")
    def signup():
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

    @app.get("/api/activate")
    def activate():
        if(token := request.args.get("token", type=str)):
            return activate_user(token)
        else: return jsonify(msg="You need a token to activate a users email", errorType="auth"), 400

    @app.post("/api/login")
    def login():
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

    @app.post("/api/requestPasswordReset")
    def requestPasswordReset():
        email = request.form['email']
        logger.info(f"Password reset request for email {email}")

        user: Optional[User] = User.query.where(
            User.email == email).one_or_none()
        if user is None:
            #do not change the output in this case since that would allow anybody to probe for emails which have an account here
            logger.info(f"  -> password reset request for unknown email address '{email}'")
        elif not send_password_reset_email(email):
            return jsonify(msg=f"Failed to send password reset email to {email}.", errorType="email"), 400

        return jsonify(msg=f"If an account with the address {email} exists, then we sent a password reset email to this address. Please check your emails"), 200

    @app.post("/api/resetPassword")
    def resetPassword():
        newPassword = request.form['newPassword']

        if not is_valid_password(newPassword): 
            return jsonify(msg = "Password invalid. The password needs to have at least one lowercase letter, uppercase letter, number, special character and at least 12 characters in total", errorType="password"), 400
        elif(token := request.args.get("token", type=str)):
            return reset_user_password(token, newPassword)
        else: return jsonify(msg="You need a token to reset a users password", errorType="auth"), 400


    @app.get("/api/userinfo")
    @jwt_required()
    def userinfo():
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

    @app.post("/api/deleteUser")
    @jwt_required()
    @confirmIdentity
    @emailModifyForAdmins
    def deleteUser(toModify: User):
        thisUser: User = current_user

        logger.info(f"user {thisUser.email} made request to delete user {toModify.email}")

        return delete_user(toModify)

    @app.post("/api/changeUserPassword")
    @jwt_required()
    @confirmIdentity
    @emailModifyForAdmins
    def changeUserPassword(toModify: User):
        thisUser: User = current_user
        newPassword = request.form['newPassword']

        if not is_valid_password(newPassword): 
            return jsonify(msg="Password invalid. The password needs to have at least one lowercase letter, uppercase letter, number, special character and at least 12 characters in total", errorType="password"), 400

        logger.info(f"user {thisUser.email} made request to modify user password of user {toModify.email}")

        toModify.set_password_unchecked(newPassword)
        return jsonify(msg="Successfully updated user password"), 200

    @app.post("/api/changeUserEmail")
    @jwt_required()
    @confirmIdentity
    @emailModifyForAdmins
    def changeUserEmail(toModify: User):
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

    @app.get("/api/resendActivationEmail")
    @jwt_required()
    def resendActivationEmail():
        user: User = current_user
        if user.activated:
            return jsonify(msg="This user is already activated", errorType="operation"), 400

        if not send_activation_email(user.email, user.email):
            return jsonify(msg=f"Failed to send password reset email to {user.email}.", errorType="email"), 400

        return jsonify(msg=f"We have sent a new password reset email to {user.email}. Please check your emails"), 200

    @app.get("/api/invalidateAllTokens")
    @jwt_required()
    def invalidateAllTokens():
        user: User = current_user
        user.invalidate_session_tokens()

        return jsonify(msg="You have successfully been logged out accross all your devices"), 200

    with app.app_context():
        db.create_all()

    return app
