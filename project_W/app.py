from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from .dependencies import db, jwt_handler
from .model import Token
from .routers import admins, users


# startup database connections before spinning up application
@asynccontextmanager
async def lifespan(_):
    await db.open()
    jwt_handler.setup(db)
    yield
    await db.close()


app = FastAPI(lifespan=lifespan)

app.include_router(users.router)
app.include_router(admins.router)


@app.post("/token")
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    user = await db.get_user_by_email_checked_password(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password",
        )
    for scope in form_data.scopes:
        if scope == "admin" and not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your user isn't an admin",
            )
    access_token = jwt_handler.create_jwt_token(
        data={"sub": user.email, "scopes": form_data.scopes}
    )
    return Token(access_token=access_token, token_type="bearer")
