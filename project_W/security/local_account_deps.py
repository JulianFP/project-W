from fastapi import HTTPException, status

from .. import dependencies as dp
from ..models.internal import DecodedAuthTokenData
from ..models.response_data import User, UserTypeEnum


async def lookup_local_user_in_db_from_token(user_token_data: DecodedAuthTokenData) -> User:
    local_user = await dp.db.get_local_user_by_email(user_token_data.email)
    if not local_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication successful, but the user was not found in database",
        )
    return User(
        id=local_user.id,
        user_type=UserTypeEnum.LOCAL,
        email=local_user.email,
        provider_name="project-W",
        is_admin=local_user.is_admin,
        is_verified=local_user.is_verified,
    )
