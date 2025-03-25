from typing import Annotated

from fastapi import APIRouter, Depends

from ..models.internal import DecodedTokenData
from ..models.response_data import ErrorResponse
from ..security.auth import validate_user

router = APIRouter(
    prefix="/api/admins",
    tags=["admins"],
    # all routes handled by this routes are authenticated
    responses={
        401: {
            "model": ErrorResponse,
            "headers": {
                "WWW-Authenticate": {
                    "type": "string",
                }
            },
        },
        403: {
            "model": ErrorResponse,
            "headers": {
                "WWW-Authenticate": {
                    "type": "string",
                }
            },
        },
    },
)


@router.get("/test")
async def admin_test(_: Annotated[DecodedTokenData, Depends(validate_user(require_admin=True))]):
    return "Only an admin is allowed to see this"
