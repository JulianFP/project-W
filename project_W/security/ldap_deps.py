import copy
from typing import Any, Awaitable, Callable

from bonsai import AuthenticationError, ConnectionError, LDAPClient, TimeoutError
from bonsai.asyncio import AIOConnectionPool, AIOLDAPConnection
from fastapi import HTTPException, status
from pydantic import ValidationError

import project_W.dependencies as dp
from project_W.logger import get_logger
from project_W.models.base import EmailValidated
from project_W.models.internal import DecodedAuthTokenData, LdapUserInfo
from project_W.models.response_data import User, UserTypeEnum
from project_W.models.settings import LdapProviderSettings

http_exc = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Incorrect username or password",
)


class LdapAdapter:
    apools: dict[str, AIOConnectionPool] = {}
    clients: dict[str, LDAPClient] = (
        {}
    )  # clients with everything preconfigured except credentials for performing binds
    ldap_prov: dict[str, LdapProviderSettings]
    logger = get_logger("project-W")

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

    async def __query_normal_user(self, idp_name: str, username: str) -> list[dict]:
        prov = self.ldap_prov[idp_name]

        async def query(conn: AIOLDAPConnection):
            if prov.user_query and (
                users := await conn.search(
                    prov.user_query.base_dn, 2, prov.user_query.filter % username
                )
            ):
                return users
            else:
                return []

        users = await self.__exec_lambda(idp_name, query)
        return users

    async def __query_admin_user(self, idp_name: str, username: str) -> list[dict]:
        prov = self.ldap_prov[idp_name]

        async def query(conn: AIOLDAPConnection):
            if prov.admin_query and (
                admins := await conn.search(
                    prov.admin_query.base_dn, 2, prov.admin_query.filter % username
                )
            ):
                return admins
            else:
                return []

        admins = await self.__exec_lambda(idp_name, query)
        return admins

    async def open(self, ldap_providers: dict[str, LdapProviderSettings]):
        self.ldap_prov = ldap_providers
        if self.ldap_prov is {}:
            raise Exception("Tried to use ldap router even though ldap is disabled in config!")
        for name, idp in self.ldap_prov.items():
            if not (idp.user_query or idp.admin_query):
                raise Exception(
                    f"The Ldap provider {name} has neither user_query nor admin_query defined. Please define at least one of them."
                )

            self.logger.info(f"Trying to connect to LDAP server {name}...")
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
            self.logger.info(f"Connected to LDAP server {name} as user {ldap_service_user}")

    async def close(self):
        self.logger.info("Closing Ldap connections...")
        for pool in self.apools.values():
            await pool.close()

    def check_idp_name(self, idp_name: str) -> bool:
        if self.ldap_prov.get(idp_name):
            return True
        else:
            return False

    async def query_user(self, idp_name, username: str) -> LdapUserInfo:
        prov = self.ldap_prov[idp_name]
        user: LdapUserInfo

        invalid_email_exc = HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The email address that Ldap returned is not valid",
        )

        if prov.admin_query and (admins := await self.__query_admin_user(idp_name, username)):
            if len(admins) > 1:
                self.logger.error(
                    f"Admin user query for user {username} returned more than one user in LDAP directory {idp_name}"
                )
                raise http_exc
            elif (
                (user_dn := admins[0].get("dn"))
                and (user_email := admins[0].get(prov.admin_query.mail_attribute_name))
                and len(user_email) > 0
            ):
                try:
                    validated_email = EmailValidated.model_validate(str(user_email[0]))
                except ValidationError:
                    raise invalid_email_exc
                user = LdapUserInfo(dn=str(user_dn), is_admin=True, email=validated_email)
            else:
                self.logger.error(
                    f"Couldn't get dn or email address for admin LDAP user {username} in LDAP directory {idp_name}"
                )
                raise http_exc
        elif prov.user_query and (users := await self.__query_normal_user(idp_name, username)):
            if len(users) > 1:
                self.logger.error(
                    f"Normal user query for user {username} returned more than one user in LDAP directory {idp_name}"
                )
                raise http_exc
            elif (
                (user_dn := users[0].get("dn"))
                and (user_email := users[0].get(prov.user_query.mail_attribute_name))
                and len(user_email) > 0
            ):
                try:
                    validated_email = EmailValidated.model_validate(str(user_email[0]))
                except ValidationError:
                    raise invalid_email_exc
                user = LdapUserInfo(dn=str(user_dn), is_admin=False, email=validated_email)
            else:
                self.logger.error(
                    f"Couldn't get dn or email address for normal LDAP user {username} in LDAP directory {idp_name}"
                )
                raise http_exc
        else:
            raise http_exc

        return user

    async def authenticate_user(self, idp_name: str, user_dn: str, password: str) -> bool:
        prov = self.ldap_prov[idp_name]
        ldap_client = copy.deepcopy(
            self.clients[idp_name]
        )  # copy so that client with credentials gets thrown away after this function
        ldap_client.set_credentials(prov.service_account_auth.mechanism, user_dn, password)
        try:
            async with ldap_client.connect(is_async=True) as conn:
                if await conn.whoami():
                    return True
                else:
                    return False
        except AuthenticationError:
            return False


ldap_adapter: LdapAdapter


async def lookup_ldap_user_in_db_from_token(user_token_data: DecodedAuthTokenData) -> User:
    ldap_user = await dp.db.get_ldap_user_by_id(int(user_token_data.sub))
    if not ldap_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication successful, but the user was not found in database",
        )
    return User(
        id=ldap_user.id,
        user_type=UserTypeEnum.LDAP,
        email=ldap_user.email,
        provider_name=ldap_user.provider_name,
        is_admin=user_token_data.is_admin,
        is_verified=user_token_data.is_verified,
    )
