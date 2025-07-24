from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

import project_W.dependencies as dp

from ._version import __git_hash__, __version__
from .caching import RedisAdapter
from .database import PostgresAdapter
from .models.base import LocalAccountOperationModeEnum
from .models.response_data import AboutResponse, AuthSettings
from .routers import admins, jobs, ldap, local_account, oidc, runners, users
from .security import ldap_deps, oidc_deps
from .smtp import SmtpClient


# startup database connections before spinning up application
@asynccontextmanager
async def lifespan(app: FastAPI):
    # connect to database
    dp.db = PostgresAdapter(str(dp.config.postgres_connection_string))
    await dp.db.open()

    # connect to caching server
    dp.ch = RedisAdapter()
    await dp.ch.open(dp.config.redis_connection)

    # connect to smtp server
    dp.smtp = SmtpClient(dp.config.smtp_server)
    await dp.smtp.open()

    # include security routers depending on which authentication backends are configured in config file
    login_method_exists = False
    if dp.config.security.oidc_providers:
        login_method_exists = True
        app.include_router(oidc.router, prefix="/api")
        await oidc_deps.register_with_oidc_providers(dp.config)
    if dp.config.security.ldap_providers:
        login_method_exists = True
        app.include_router(ldap.router, prefix="/api")
        ldap_deps.ldap_adapter = ldap_deps.LdapAdapter()
        await ldap_deps.ldap_adapter.open(dp.config.security.ldap_providers)
    if dp.config.security.local_account.mode != LocalAccountOperationModeEnum.DISABLED:
        login_method_exists = True
        app.include_router(local_account.router, prefix="/api")
        for prov_num, prov_user in dp.config.security.local_account.user_provisioning.items():
            await dp.db.ensure_local_user_is_provisioned(
                prov_num, prov_user.email, prov_user.password, prov_user.is_admin
            )
    if not login_method_exists:
        raise Exception(
            "No login method (one of local_account, ldap or oidc) has been specified in the config!"
        )

    # include app mount (it is important that this happens after all routers have been included!)
    if dp.client_path is not None:
        app.mount(
            "/",
            StaticFiles(directory=dp.client_path.resolve(), html=True),
            name="client app",
        )

    # enqueue all jobs from the database that are not finished yet
    for job_id, user_id, aborting in await dp.db.get_all_unfinished_jobs():
        if aborting:
            await dp.db.finish_failed_job(job_id, "Job was aborted")
        await dp.ch.enqueue_new_job(job_id, job_id * -1)
        await dp.ch.assign_job_to_runner_if_possible(job_id, user_id)

    yield

    # close connections before application exit
    await dp.db.close()
    await dp.ch.close()
    await dp.smtp.close()
    await ldap_deps.ldap_adapter.close()


# this can be in Markdown
app_description = """
## About Project-W

Project-W is a platform for creating transcripts of audio files (speech-to-text). It leverages OpenAIs Whisper models for the transcription while providing an API and easy-to-use interface for users to create and manage transcription jobs.

## More documentation

In addition to [the OpenAPI doc](/docs) there is also [a Redoc doc](/redoc) available if you prefer.

If you are looking for documentation about something else than the API then refer to the [full Project-W documentation](https://project-w.readthedocs.io). You can also find the source code of all Project-W components on GitHub:
- [Backend](https://github.com/julianfp/project-w)
- [Frontend](https://github.com/julianfp/project-w-frontend)
- [Runner](https://github.com/julianfp/project-w-runner)
"""
app_tags_metadata = [
    {
        "name": "users",
        "description": "For regular users to manage their accounts",
    },
    {
        "name": "local-account",
        "description": "Login, Signup and account management routes for local Project-W accounts",
    },
    {
        "name": "oidc",
        "description": "Login/Signup routes for OIDC authentication providers. If no routes are shown here then this instance has no OIDC provider configured.",
    },
    {
        "name": "ldap",
        "description": "Login/Signup routes for LDAP authentication providers. If no routes are shown here then this instance has no LDAP provider configured.",
    },
    {
        "name": "jobs",
        "description": "Job submission and management routes",
    },
    {
        "name": "admins",
        "description": "For admin users to manage the server and all users on it",
    },
    {
        "name": "runners",
        "description": "Routes used by Project-W runners to communicate with the backend, retrieve jobs and submit transcripts",
    },
]

app = FastAPI(
    title="Project-W",
    description=app_description,
    summary="Create transcripts of audio files (speech-to-text)!",
    version=__version__,
    license_info={
        "name": "GNU Affero General Public License Version 3",
        "identifier": "AGPL-3.0-only",
        "url": "https://www.gnu.org/licenses/agpl-3.0.txt",
    },
    openapi_tags=app_tags_metadata,
    lifespan=lifespan,
    root_path=(
        dp.config.web_server.reverse_proxy.root_path
        if dp.config.web_server.reverse_proxy and dp.config.web_server.reverse_proxy.root_path
        else ""
    ),
    root_path_in_servers=False,
    # add imprint info to app attributes (so that it is displayed in OpenAPI docs as well)
    contact=(
        {
            "name": dp.config.imprint.name,
            "email": dp.config.imprint.email.root,
            "url": f"{dp.config.client_url}/imprint",
        }
        if dp.config.imprint
        else None
    ),
    terms_of_service=f"{dp.config.client_url}/tos" if dp.config.terms_of_services else None,
)
# middleware required by authlib for oidc
app.add_middleware(
    SessionMiddleware,
    secret_key=dp.config.security.local_token.session_secret_key.root.get_secret_value(),
)
# middleware to guard against HTTP Host header attacks
app.add_middleware(TrustedHostMiddleware, allowed_hosts=dp.config.web_server.allowed_hosts)
# middleware to handle proxy headers and rewrite Host header accordingly
if dp.config.web_server.reverse_proxy is not None:
    app.add_middleware(
        ProxyHeadersMiddleware, trusted_hosts=dp.config.web_server.reverse_proxy.trusted_proxies
    )

app.include_router(users.router, prefix="/api")
app.include_router(admins.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(runners.router, prefix="/api")


@app.get("/api/about")
async def about() -> AboutResponse:
    """
    Returns a brief description of Project-W, a link to the backend's GitHub repository, the backend's version currently running on the system as well as the imprint of this instance (if it was configured by the instance's admin).
    """
    return AboutResponse(
        description="A self-hostable platform on which users can create transcripts of their audio files (speech-to-text) using Whisper AI",
        source_code="https://github.com/JulianFP/project-W",
        version=__version__,
        git_hash=__git_hash__.removeprefix("g"),
        imprint=dp.config.imprint,
        terms_of_services=dp.config.terms_of_services,
        job_retention_in_days=dp.config.cleanup.finished_job_retention_in_days,
        site_banners=await dp.db.list_site_banners(),
    )


@app.get("/api/auth_settings")
async def auth_settings() -> AuthSettings:
    """
    Returns all information required by the client regarding which account types and identity providers this instance supports, whether account signup of local accounts is allowed, whether the creation of API tokens is allowed for each account type and so on.
    """
    return AuthSettings(
        local_account=dp.config.security.local_account,
        oidc_providers=dp.config.security.oidc_providers,
        ldap_providers=dp.config.security.ldap_providers,
    )
