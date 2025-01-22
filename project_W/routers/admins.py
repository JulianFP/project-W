from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from ..model import ErrorResponse, UserInDb
from ..security import validate_admin_user

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
async def admin_test(_: Annotated[UserInDb, Depends(validate_admin_user)]):
    return "Only an admin is allowed to see this"
