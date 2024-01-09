from typing import Optional, Dict
from itsdangerous.url_safe import URLSafeTimedSerializer
from project_W.logger import get_logger
from flask import json

logger = get_logger("project-W")

def _encode_string_as_token(string_to_encode: str, salt: str, secret_key: str) -> str:
    ss = URLSafeTimedSerializer(secret_key, salt=salt)
    return ss.dumps(string_to_encode)

def _decode_string_from_token(
    token: str, salt: str, secret_key: str, max_age_secs: int
) -> Optional[str]:
    ss = URLSafeTimedSerializer(secret_key, salt=salt)
    try:
        decodedString = ss.loads(token, max_age=max_age_secs)
    except Exception as e:
        logger.warning(f"Invalid or expired {salt} token: {e}")
        return None
    return decodedString


def encode_activation_token(oldEmail: str, newEmail: str, secret_key: str) -> str:
    return _encode_string_as_token(json.dumps({"old_email": oldEmail, "new_email": newEmail}), "activate", secret_key)

def decode_activation_token(token: str, secret_key: str) -> Dict|None:
    one_day_in_secs = 60 * 60 * 24
    decodedData = _decode_string_from_token(token, "activate", secret_key, one_day_in_secs)
    if decodedData is None:
        return None
    else:
        decodedDict = json.loads(decodedData)
        return decodedDict

def encode_password_reset_token(email: str, secret_key: str) -> str:
    return _encode_string_as_token(email, "password-reset", secret_key)

def decode_password_reset_token(token: str, secret_key: str) -> Optional[str]:
    one_hour_in_secs = 60 * 60
    return _decode_string_from_token(
        token, "password-reset", secret_key, one_hour_in_secs
    )
