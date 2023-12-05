import datetime
import secrets
from typing import Optional
from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, create_access_token, current_user, jwt_required
from .logger import get_logger
from .model import User, add_new_user, delete_user, db, activate_user, send_activation_email
from .config import loadConfig


def create_app() -> Flask:
    logger = get_logger("project-W")
    app = Flask("project-W")

    #load config from default values < config file < env vars (latest has highest precedence)
    loadConfig(app)

    #check syntax of JWT_SECRET_KEY and update if necessary
    JWT_SECRET_KEY = app.config["JWT_SECRET_KEY"]
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
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = datetime.timedelta(minutes=60)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{app.config['DB_PATH']}/database.db"
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

    @app.get("/api/activate")
    def activate():
        if(token := request.args.get("token", type=str)):
            return activate_user(token)
        else: return "You need a token to activate a users email", 400

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
        toModify.set_password_unchecked(new_password)
        return jsonify(message="Successfully updated user password"), 200

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
        send_activation_email(toModify.email, new_email)
        return jsonify(message="Successfully requested email address change. Please confirm your new address be clicking on the link provided in the email we just sent you"), 200

    with app.app_context():
        db.create_all()

    return app
