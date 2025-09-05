import copy
from typing import Any, Awaitable, Callable

from bonsai import AuthenticationError, ConnectionError, LDAPClient, TimeoutError
from bonsai.asyncio import AIOConnectionPool, AIOLDAPConnection
from fastapi import HTTPException, status
from pydantic import ValidationError

import project_W.dependencies as dp

from ..logger import get_logger
from ..models.base import EmailValidated
from ..models.internal import LdapTokenInfoInternal, LdapUserInfo
from ..models.settings import LdapProviderSettings

http_exc = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Incorrect username or password",
)

logger = get_logger("project-W")


class LdapAdapter:
    apools: dict[str, AIOConnectionPool] = {}
    clients: dict[
        str, LDAPClient
    ] = {}  # clients with everything preconfigured except credentials for performing binds
    ldap_prov: dict[str, LdapProviderSettings]

    async def __exec_lambda(
        self, idp_name: str, func: Callable[[AIOLDAPConnection], Awaitable[Any]]
    ) -> Any:
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

    async def __query_normal_user_with_username(self, idp_name: str, username: str) -> list[dict]:
        prov = self.ldap_prov[idp_name]

        async def query(conn: AIOLDAPConnection):
            if prov.user_query is not None:
                filter_expression = ""
                for user_attr in prov.username_attributes:
                    filter_expression += f"({user_attr}={username})"
                filter_expression = f"(&({prov.user_query.filter})(|{filter_expression}))"
                if users := await conn.search(prov.user_query.base_dn, 2, filter_expression):
                    return users
            return []

        users = await self.__exec_lambda(idp_name, query)
        return users

    async def __query_normal_user_with_uid(self, idp_name: str, uid: str) -> list[dict]:
        prov = self.ldap_prov[idp_name]

        async def query(conn: AIOLDAPConnection):
            if prov.user_query is not None:
                filter_expression = f"(&({prov.user_query.filter})({prov.uid_attribute}={uid}))"
                if users := await conn.search(prov.user_query.base_dn, 2, filter_expression):
                    return users
            return []

        users = await self.__exec_lambda(idp_name, query)
        return users

    async def __query_admin_user_with_username(self, idp_name: str, username: str) -> list[dict]:
        prov = self.ldap_prov[idp_name]

        async def query(conn: AIOLDAPConnection):
            if prov.admin_query is not None:
                filter_expression = ""
                for admin_attr in prov.username_attributes:
                    filter_expression += f"({admin_attr}={username})"
                filter_expression = f"(&({prov.admin_query.filter})(|{filter_expression}))"
                if admins := await conn.search(prov.admin_query.base_dn, 2, filter_expression):
                    return admins
            return []

        admins = await self.__exec_lambda(idp_name, query)
        return admins

    async def __query_admin_user_with_uid(self, idp_name: str, uid: str) -> list[dict]:
        prov = self.ldap_prov[idp_name]

        async def query(conn: AIOLDAPConnection):
            if prov.admin_query is not None:
                filter_expression = f"(&({prov.admin_query.filter})({prov.uid_attribute}={uid}))"
                if users := await conn.search(prov.admin_query.base_dn, 2, filter_expression):
                    return users
            return []

        users = await self.__exec_lambda(idp_name, query)
        return users

    async def __process_query_result(
        self, idp_name: str, result: list[dict], is_admin: bool
    ) -> LdapUserInfo:
        prov = self.ldap_prov[idp_name]
        if len(result) > 1:
            logger.error(f"LDAP query returned more than one user in LDAP directory {idp_name}")
            raise http_exc
        elif (
            (user_uid := result[0].get(prov.uid_attribute))
            and len(user_uid) > 0
            and (user_dn := result[0].get("dn"))
            and (user_email := result[0].get(prov.mail_attribute))
            and len(user_email) > 0
        ):
            try:
                validated_email = EmailValidated.model_validate(str(user_email[0]))
            except ValidationError:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="The email address that Ldap returned is not valid",
                )
            return LdapUserInfo(
                dn=str(user_dn), uid=str(user_uid[0]), is_admin=is_admin, email=validated_email
            )
        else:
            logger.error(
                f"Couldn't get uid or email address for LDAP user in LDAP directory {idp_name}"
            )
            raise http_exc

    async def open(self, ldap_providers: dict[str, LdapProviderSettings]):
        self.ldap_prov = ldap_providers
        if self.ldap_prov == {}:
            raise Exception("Tried to use ldap router even though ldap is disabled in config!")
        for name, idp in self.ldap_prov.items():
            if not (idp.user_query or idp.admin_query):
                raise Exception(
                    f"The Ldap provider {name} has neither user_query nor admin_query defined. Please define at least one of them."
                )

            logger.info(f"Trying to connect to LDAP server {name}...")
            ldap_client = LDAPClient(str(idp.server_address))
            if idp.ca_pem_file_path:
                ldap_client.set_ca_cert(str(idp.ca_pem_file_path))
            self.clients[name] = copy.deepcopy(ldap_client)
            ldap_client.set_credentials(
                idp.service_account_auth.mechanism,
                idp.service_account_auth.user,
                idp.service_account_auth.password.get_secret_value(),
            )

            self.apools[name] = AIOConnectionPool(ldap_client, 5, 10)
            await self.apools[name].open()

            async def func(conn: AIOLDAPConnection):
                return await conn.whoami()

            ldap_service_user = await self.__exec_lambda(name, func)
            logger.info(f"Connected to LDAP server {name} as user {ldap_service_user}")

    async def close(self):
        logger.info("Closing Ldap connections...")
        for pool in self.apools.values():
            await pool.close()

    def check_idp_name(self, idp_name: str) -> bool:
        if self.ldap_prov.get(idp_name):
            return True
        else:
            return False

    async def query_user_with_username(self, idp_name: str, username: str) -> LdapUserInfo:
        prov = self.ldap_prov[idp_name]
        if prov.admin_query and (
            admins := await self.__query_admin_user_with_username(idp_name, username)
        ):
            return await self.__process_query_result(idp_name, admins, True)
        elif prov.user_query and (
            users := await self.__query_normal_user_with_username(idp_name, username)
        ):
            return await self.__process_query_result(idp_name, users, False)
        else:
            raise http_exc

    async def query_user_with_uid(self, idp_name: str, uid: str) -> LdapUserInfo:
        prov = self.ldap_prov[idp_name]
        if prov.admin_query and (admins := await self.__query_admin_user_with_uid(idp_name, uid)):
            return await self.__process_query_result(idp_name, admins, True)
        elif prov.user_query and (users := await self.__query_normal_user_with_uid(idp_name, uid)):
            return await self.__process_query_result(idp_name, users, False)
        else:
            raise http_exc

    async def authenticate_user(self, idp_name: str, dn: str, password: str) -> bool:
        prov = self.ldap_prov[idp_name]
        ldap_client = copy.deepcopy(
            self.clients[idp_name]
        )  # copy so that client with credentials gets thrown away after this function
        ldap_client.set_credentials(prov.service_account_auth.mechanism, dn, password)
        try:
            async with ldap_client.connect(is_async=True) as conn:
                if await conn.whoami():
                    return True
                else:
                    return False
        except AuthenticationError:
            return False


ldap_adapter: LdapAdapter


async def invalidate_token_if_ldap_user_lost_privileges(
    ldap_adapter: LdapAdapter, token: LdapTokenInfoInternal
):
    try:
        ldap_user = await ldap_adapter.query_user_with_uid(token.provider_name, token.uid)
        if not ldap_user.is_admin and token.admin_privileges:
            await dp.db.delete_token_of_user(token.user_id, token.id)
            logger.info(
                f"Invalidated admin token with id {token.id} of LDAP user {token.user_id} because user doesn't have admin privileges anymore"
            )
    except HTTPException:
        await dp.db.delete_token_of_user(token.user_id, token.id)
        logger.info(
            f"Invalidated token with id {token.id} of LDAP user {token.user_id} because user couldn't be found at LDAP provider with all necessary attributes"
        )
