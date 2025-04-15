from typing import Annotated, Any, Awaitable, Callable

from bonsai import ConnectionError, LDAPClient, TimeoutError
from bonsai.asyncio import AIOConnectionPool, AIOLDAPConnection
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from project_W.logger import get_logger
from project_W.models.settings import LdapProviderSettings

router = APIRouter(
    prefix="/ldap",
    tags=["ldap"],
)


class LdapAdapter:
    apools: dict[str, AIOConnectionPool] = {}
    ldap_prov: dict[str, LdapProviderSettings]
    logger = get_logger("project-W")

    async def __exec_lambda(
        self, idp_name: str, func: Callable[[AIOLDAPConnection], Awaitable[Any]]
    ):
        idle_count = self.apools[idp_name].idle_connection
        for tries in range(idle_count + 1):
            async with self.apools[idp_name].spawn() as conn:
                try:
                    return await func(conn)
                except (ConnectionError, TimeoutError) as e:
                    conn.close()
                    # If all of the idle connections have been tried and the
                    # call still failed, there is something deeper wrong.
                    if tries == idle_count:
                        raise e

    async def open(self, ldap_providers: dict[str, LdapProviderSettings]):
        self.ldap_prov = ldap_providers
        if self.ldap_prov is {}:
            raise Exception("Tried to use ldap router even though ldap is disabled in config!")
        for name, idp in self.ldap_prov.items():
            self.logger.info(f"Trying to connect to LDAP server {name}...")
            ldap_client = LDAPClient(idp.server_address)
            if idp.ca_pem_file_path:
                ldap_client.set_ca_cert(idp.ca_pem_file_path)
                ldap_client.set_cert_policy("allow")  # TODO
            ldap_client.set_credentials(
                idp.service_account_auth.mechanism,
                idp.service_account_auth.user,
                idp.service_account_auth.password,
            )

            self.apools[name] = AIOConnectionPool(ldap_client, 5, 10)
            await self.apools[name].open()

            async def func(conn: AIOLDAPConnection):
                return await conn.whoami()

            ldap_service_user = await self.__exec_lambda(name, func)
            self.logger.info(f"Connected to LDAP server {name} as user {ldap_service_user}")

    async def auth_user(self, idp_name: str, username: str, password: str):
        prov = self.ldap_prov.get(idp_name)
        if not prov:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not authenticate user, ldap server {idp_name} not known",
            )

        async def query(conn: AIOLDAPConnection):
            if prov.admin_query and (
                admin_user := await conn.search(
                    prov.admin_query.base_dn, 2, prov.admin_query.filter % username
                )
            ):
                return admin_user
            if prov.user_query and (
                normal_user := await conn.search(
                    prov.user_query.base_dn, 2, prov.user_query.filter % username
                )
            ):
                return normal_user
            return None

        user = await self.__exec_lambda(idp_name, query)
        print(user)
        return user


ldap_adapter: LdapAdapter


@router.post("/login/{idp_name}")
async def login(idp_name: str, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    return await ldap_adapter.auth_user(idp_name, form_data.username, form_data.password)
