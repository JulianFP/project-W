import base64
import hashlib
import secrets
from abc import ABC, abstractmethod
from datetime import datetime
from typing import AsyncGenerator, LiteralString

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import UploadFile
from psycopg import pq
from psycopg.connection_async import AsyncConnection
from psycopg.rows import class_row, scalar_row
from psycopg.types.json import Jsonb
from psycopg_pool.pool_async import AsyncConnectionPool
from pydantic import SecretStr

from ._version import version, version_tuple
from .logger import get_logger
from .models.base import EmailValidated, JobBase, PasswordValidated
from .models.internal import (
    JobSettingsInDb,
    JobSortKey,
    LdapUserInDb,
    LocalUserInDb,
    OidcUserInDb,
    OnlineRunner,
    RunnerInDb,
    TokenSecret,
)
from .models.request_data import JobSettings, Transcript, TranscriptTypeEnum
from .models.response_data import JobAndSettings, RunnerCreatedInfo, TokenSecretInfo
from .utils import parse_version_tuple


class DatabaseAdapter(ABC):
    """
    Important semantics:
    This class is designed to be used together with startup/shutdown hooks of a web framework, specifically the lifespan function in FastAPI
    As such before any other method of this class can be used the open() method should be called and before shutdown the close() method should be called
    many private methods (prefixed with __) do not create or close transactions (since they do not get their own connection). Instead other non-private methods are expected to lend them their connection. This way we can combine the same sql queries in multiple transactions while reusing the same code
    """

    hasher = PasswordHasher()
    logger = get_logger("project-W")

    @abstractmethod
    def __init__(self, connection_string: str) -> None:
        pass

    @abstractmethod
    async def open(self):
        """
        This method should initiate the databse connection(s), make sure the schema, tables and metadata exist and are valid by creating them if missing or migrating them from an older version. All of that should be part of a single transaction. This method will be called before any other of this class.
        """
        pass

    @abstractmethod
    async def close(self):
        """
        This method should close all transactions and connections and do anything else that needs to be done before the application can savely shutdown. This method will be called last after any other of this class.
        """
        pass

    @abstractmethod
    async def _add_local_user_hashed(
        self,
        email: EmailValidated,
        hashed_password: str,
        is_admin: bool = False,
        is_verified: bool = False,
    ) -> int | None:
        """
        This method creates a new user if it doesn't exist yet. The password is already hashed here which is the reason why this method is protected. It should not be used outside of this base class, use add_new_user instead!
        Returns the user id of the created user
        Returns None if a user with this email already exists.
        """
        pass

    async def add_local_user(
        self,
        email: EmailValidated,
        password: PasswordValidated,
        is_admin: bool = False,
        is_verified: bool = False,
    ) -> int | None:
        """
        Create a new user if it doesn't exist yet. The password will be hashed in this function before writing it in the database.
        Returns the user id of the created user
        Returns None if a user with this email already exists.
        """
        hashed_password = self.hasher.hash(password.root.get_secret_value())
        return await self._add_local_user_hashed(email, hashed_password, is_admin, is_verified)

    @abstractmethod
    async def _ensure_local_user_is_provisioned_hashed(
        self,
        provision_number: int,
        email: EmailValidated,
        hashed_password: str,
        is_admin: bool = False,
    ) -> int:
        """
        This method provisions a user from the config file. Compared to add_local_user it also checks the provision_number and changes the users email, password and admin privileges if they have changed.
        Returns the user id of the user
        """
        pass

    async def ensure_local_user_is_provisioned(
        self,
        provision_number: int,
        email: EmailValidated,
        password: PasswordValidated,
        is_admin: bool = False,
    ) -> int:
        """
        Provision a user from the config file. The password will be hashed in this function before writing it in the database.
        Returns the user id of the user
        """
        hashed_password = self.hasher.hash(password.root.get_secret_value())
        return await self._ensure_local_user_is_provisioned_hashed(
            provision_number, email, hashed_password, is_admin
        )

    @abstractmethod
    async def ensure_oidc_user_exists(self, iss: str, sub: str, email: EmailValidated) -> int:
        """
        Add a database entry for an oidc user if it doesn't exist yet. Will be called at first login of this user.
        If the user exists but with a different email then update the email address of the user.
        Returns the user id of the created user
        """
        pass

    @abstractmethod
    async def ensure_ldap_user_exists(
        self, provider_name: str, dn: str, email: EmailValidated
    ) -> int:
        """
        Add a database entry for an ldap user if it doesn't exist yet. Will be called at first login of this user.
        If the user exists but with a different email then update the email address of the user.
        Returns the user id of the user
        """
        pass

    @abstractmethod
    async def get_new_token_for_user(self, user_id: int, name: str) -> TokenSecret:
        """
        Create a new api token and return it
        """
        pass

    @abstractmethod
    async def delete_user(self, user_id: int):
        """
        Delete the user with id user_id.
        """
        pass

    @abstractmethod
    async def delete_token_secret_of_user(self, user_id: int, token_id: int):
        """
        Delete the token secret with id token_id if it belongs to user with id user_id.
        """
        pass

    @abstractmethod
    async def delete_all_token_secrets_of_user(self, user_id: int):
        """
        Delete all token secrets of user with id user_id
        """
        pass

    @abstractmethod
    async def delete_jobs_of_user(self, user_id: int, job_ids: list[int]):
        """
        Delete all provided jobs of the provided user
        """
        pass

    @abstractmethod
    async def get_local_user_by_email(self, email: EmailValidated) -> LocalUserInDb | None:
        """
        Return a local user with the matching email, or None if the email doesn't match any user
        """
        pass

    @abstractmethod
    async def get_oidc_user_by_iss_sub(self, iss: str, sub: str) -> OidcUserInDb | None:
        """
        Return an oidc user with the matching iss/sub pair, or None if iss/sub doesn't match any user
        """
        pass

    @abstractmethod
    async def get_ldap_user_by_id(self, user_id: int) -> LdapUserInDb | None:
        """
        Return an ldap user with the matching user id, or None if user_id doesn't match any user
        """
        pass

    @abstractmethod
    async def get_token_secret_of_user(self, user_id: int, token_id: int) -> TokenSecret | None:
        """
        Return the token secret object that matches both the token id and user id, or None if there are no matches
        """
        pass

    @abstractmethod
    async def get_temp_session_token_secret_of_user(self, user_id: int) -> TokenSecret | None:
        """
        Return the token secret object that is used to sign temporary session tokens of a user, or None if there are no matches
        """
        pass

    @abstractmethod
    async def get_info_of_all_tokens_of_user(self, user_id: int) -> list[TokenSecretInfo]:
        """
        Return a list of all stripped token secret objects a user has
        """
        pass

    @abstractmethod
    async def _update_password_hash(self, user_id: int, new_password_hash: str):
        """
        Sometimes passwords need rehashing. This function implements that.
        It gets called every time a password for a user is checked in 'get_user_by_email_checked_password'
        """
        pass

    async def get_local_user_by_email_checked_password(
        self, email: EmailValidated, password: SecretStr
    ) -> LocalUserInDb | None:
        """
        Return a user with the matching email if the provided password is also correct, or None if the email doesn't match any user or the password is incorrect
        Basically 'get_local_user_by_email' with builtin password checker
        """
        user = await self.get_local_user_by_email(email)
        if user is None:
            return None

        try:
            self.hasher.verify(user.password_hash, password.get_secret_value())
        except VerificationError:
            return None

        if self.hasher.check_needs_rehash(user.password_hash):
            await self._update_password_hash(user.id, self.hasher.hash(password.get_secret_value()))

        return user

    @abstractmethod
    async def verify_local_user(self, user_id: int, new_email: EmailValidated):
        """
        Update a local user to be verified.
        Update the email address to new_email as well.
        """
        pass

    @abstractmethod
    async def _update_local_user_password(
        self,
        email: EmailValidated,
        hashed_new_password: str,
    ) -> int | None:
        """
        This method updates the password of an existing local user.
        Returns the user id of the user whose password was updated.
        Returns None if no user with this email exists.
        """
        pass

    async def update_local_user_password(
        self,
        email: EmailValidated,
        new_password: PasswordValidated,
    ) -> int | None:
        """
        Create a new user if it doesn't exist yet. The password will be hashed in this function before writing it in the database.
        Returns the user id of the created user
        Returns None if a user with this email already exists.
        """
        hashed_new_password = self.hasher.hash(new_password.root.get_secret_value())
        return await self._update_local_user_password(email, hashed_new_password)

    @abstractmethod
    async def _create_runner_hashed(self, token_hash: str) -> int:
        """
        INSERT a new runner with the provided token_hash into the database
        Return the id of the newly created runner
        """
        pass

    def __runner_token_hash(self, token: str):
        """
        We only store the hash of the token, otherwise a db leak would make
        it possible to impersonate any runner. We don't need to use a salted hash
        because the token is created by the server and already has sufficient entropy.
        The hash itself is stored using base64.
        """
        return (
            base64.urlsafe_b64encode(hashlib.sha256(token.encode("ascii")).digest())
            .rstrip(b"=")
            .decode("ascii")
        )

    @abstractmethod
    async def add_new_job_settings(
        self, user_id: int, job_settings: JobSettings, is_new_default: bool = False
    ) -> int:
        """
        Create a new set of job settings for the user with id user_id and return its id
        If is_new_default is true then make that new set of settings the new default for this user
        """
        pass

    @abstractmethod
    async def get_default_job_settings_of_user(self, user_id: int) -> JobSettings | None:
        """
        Return the job settings of that user that are marked as the default
        Returns None if the user doesn't have any default settings
        """
        pass

    @abstractmethod
    async def get_job_settings_by_job_id(self, job_id: int) -> JobSettings | None:
        """
        Return the job settings that are the job with the job id job_id has
        Returns None if no job with id job_id exists
        """
        pass

    @abstractmethod
    async def add_new_job(
        self, user_id: int, audio_file: UploadFile, job_settings_id: int | None = None
    ) -> int | None:
        """
        Create a new job of the provided user and with the provided audio file and job settings
        If provided job_settings_id is None then use the default job settings of that user
        Returns None if the user doesn't own job_settings with id job_settings_id
        """
        pass

    @abstractmethod
    async def get_total_number_of_jobs_of_user(
        self, user_id: int, excl_finished: bool, excl_downloaded: bool
    ) -> int:
        """
        Get total number of jobs that a user has (after optionally excluding finished and/or downloaded jobs)
        """
        pass

    @abstractmethod
    async def get_top_k_job_ids_of_user(
        self,
        user_id: int,
        k: int,
        sort_key: JobSortKey,
        desc: bool,
        excl_finished: bool,
        excl_downloaded: bool,
    ) -> list[int]:
        """
        Query the first k jobs sorted by sort_key (descending if desc = True, ascending otherwise) of user_id
        """
        pass

    @abstractmethod
    async def get_job_infos_of_user(self, user_id: int, job_ids: list[int]) -> list[JobBase]:
        """
        Returns all job metadata (excluding job settings, audio/audio oid, user_id, job_settings_id and transcript) for all provided job ids that belong to the provided user_id
        """
        pass

    @abstractmethod
    async def get_job_infos_with_settings_of_user(
        self, user_id: int, job_ids: list[int]
    ) -> list[JobAndSettings]:
        """
        Returns all job metadata (including job settings but excluding audio/audio oid, user_id, job_settings_id and transcript) for all provided job ids that belong to the provided user_id
        """
        pass

    @abstractmethod
    async def get_job_audio(self, job_id: int) -> AsyncGenerator[bytes, None]:
        """
        This is a python generator that returns chunks of the binary file (in __file_chunk_size_in_bytes increments)
        Use this like any other python async generator (i.e. file open-like interface)
        Binary is only read from database one chunk at a time instead of the whole file at once.
        """
        yield b""  # type annotation needs this for some reason even though this is an abstract method

    @abstractmethod
    async def get_job_transcript_of_user(
        self, user_id: int, job_id: int, transcript_type: TranscriptTypeEnum
    ) -> str | dict | None:
        """
        Returns the transcript object of a finished job belonging to that user
        Returns None if no job with that id exists or if that job doesn't have a transcript (yet)
        """
        pass

    @abstractmethod
    async def get_all_ids_of_unfinished_jobs(self) -> list[int]:
        """
        Returns all jobs in the database that haven't finished yet (not downloaded, finished, failed).
        Will be called at startup to enqueue existing jobs
        """
        pass

    @abstractmethod
    async def finish_successful_job(self, runner: OnlineRunner, transcript: Transcript):
        """
        Mark the job with id job_id as successfully finished by adding all the submitted information to it (if that job exists)
        """
        pass

    @abstractmethod
    async def finish_failed_job(
        self, job_id: int, error_msg: str, runner: OnlineRunner | None = None
    ):
        """
        Mark the job with id job_id as unsuccessfully finished by adding all the submitted information to it (if that job exists).
        Note that in contrary to finish_successful_job here OnlineRunner is optional because the job might have failed before it was assigned to a runner (e.g. if it was aborted)
        """
        pass

    @abstractmethod
    async def _get_runner_by_token_hashed(self, token_hash: str) -> int | None:
        """
        Returns the id of the runner with the matching token_hash
        Returns None if no Runner matches
        """
        pass

    async def create_runner(self) -> RunnerCreatedInfo:
        """
        Creates a new runner, inserts it into the database and returns its newly generated token
        token generation is done here because it is important that the token is sever generated (because of how it is hashed)
        """
        token = secrets.token_urlsafe()
        token_hash = self.__runner_token_hash(token)

        # Sanity check to ensure that the token and its hash are unique.
        while (await self._get_runner_by_token_hashed(token_hash)) is not None:
            token = secrets.token_urlsafe()
            token_hash = self.__runner_token_hash(token)

        runner_id = await self._create_runner_hashed(token_hash)
        return RunnerCreatedInfo(id=runner_id, token=token)

    async def get_runner_by_token(self, token: str) -> int | None:
        token_hash = self.__runner_token_hash(token)
        return await self._get_runner_by_token_hashed(token_hash)


class PostgresAdapter(DatabaseAdapter):
    apool: AsyncConnectionPool
    schema: LiteralString = "project_w"
    minimal_required_postgres_version = 14  # for both postgres and libpq
    __file_chunk_size_in_bytes = 10240  # 10MiB

    def __init__(self, connection_string: str) -> None:
        self.apool = AsyncConnectionPool(
            conninfo=connection_string,
            open=False,
            check=AsyncConnectionPool.check_connection,
        )

    async def open(self):
        self.logger.info("Trying to connect to PostgreSQL database...")

        # make sure libpq version is at least the minimal supported one. Do this first because it doesn't even require connecting to the database
        self.__ensure_psycopg_libpq_version()

        await self.apool.open()
        await self.apool.wait()  # this waits until all connections are established. This makes sure that the backend can properly talk to the database before it accepts clients
        self.logger.info("Successfully connected to database. Preparing database now...")

        async with self.apool.connection() as conn:
            # ensure that the postgresql database version is at least the minimal supported one
            await self.__ensure_postgresql_version(conn)

            table_names: list[LiteralString] = [
                "users",
                "local_accounts",
                "oidc_accounts",
                "ldap_accounts",
                "runners",
                "job_settings",
                "jobs",
                "transcripts",
                "token_secrets",
            ]

            if not await self.__check_schema_exists(conn, self.schema):
                await self.__create_schema(conn, self.schema)

                # also create all other tables to skip their existence checks and migration code since there can't be any tables in a newly created schema anyway
                await self.__create_all_tables(conn)
            elif not await self.__check_table_exists(conn, "metadata"):
                # if the metadata is missing we can't know whether and how to do a migration on the other table. Because of this we throw an exception if the metadata table is missing but any other table exists to be safe
                for table_name in table_names:
                    if await self.__check_table_exists(conn, table_name):
                        raise Exception(
                            f"Critical: The metadata table is missing but the {table_name} table still exists. Either restore the metadata table with its previous contents or drop the {table_name} table!"
                        )

                # if all tables where missing but the schema existed for some reason then ignore that and just create all the tables in that schema
                await self.__create_all_tables(conn)
            else:
                # if schema and metadata table already existed we still have to check if all the other tables still exist
                # no table can be dropped on its own
                # do database migration before creating any missing tables because those created tables would have the new format which would brick the migration code
                await self.__update_database_schema_if_needed(conn)

                for table_name in table_names:
                    if not await self.__check_table_exists(conn, table_name):
                        raise Exception(
                            f"Critical: The metadata table exists but the {table_name} table is missing. Either restore the {table_name} table with its previous contents or drop the metadata table as well!"
                        )

        self.logger.info("Database is ready to use")

    async def close(self):
        self.logger.info("Closing PostgreSQL connections...")
        await self.apool.close()

    async def __ensure_postgresql_version(self, conn: AsyncConnection):
        async with conn.cursor(row_factory=scalar_row) as cur:
            await cur.execute(
                """
                SHOW server_version
            """
            )
            version_string = await cur.fetchone()
            if not version_string:
                raise Exception("Couldn't read the version of the specified PostgreSQL database")
            if int(version_string[0:2]) < self.minimal_required_postgres_version:
                raise Exception(
                    f"The version of the specified PostgreSQL database is {version_string} while the minimal required version is {self.minimal_required_postgres_version}"
                )
            self.logger.info(f"PostgreSQL server is on version {version_string}")

    def __ensure_psycopg_libpq_version(self):
        version_string = pq.version()
        if int(str(version_string)[0:2]) < self.minimal_required_postgres_version:
            raise Exception(
                f"The version of libpq loaded by psycopg is {version_string} while the minimal required version is {self.minimal_required_postgres_version}"
            )
        self.logger.info(f"PostgreSQL libpq is on version {version_string}")

    async def __check_schema_exists(
        self, conn: AsyncConnection, schema_name: LiteralString
    ) -> bool:
        self.logger.info(f"Checking if schema {schema_name} exists...")
        async with conn.cursor(row_factory=scalar_row) as cur:
            await cur.execute(
                f"""
                SELECT EXISTS (
                    SELECT *
                    FROM information_schema.schemata
                    WHERE
                        schema_name = '{schema_name}'
                )
            """
            )
            exists = await cur.fetchone()
            if exists is not None:
                return exists
            else:
                return False

    async def __check_table_exists(self, conn: AsyncConnection, table_name: LiteralString):
        self.logger.info(f"Checking if {table_name} table exists...")
        async with conn.cursor(row_factory=scalar_row) as cur:
            await cur.execute(
                f"""
                SELECT EXISTS (
                    SELECT *
                    FROM information_schema.tables
                    WHERE
                        table_schema = '{self.schema}' AND
                        table_type = 'BASE TABLE' AND
                        table_name = '{table_name}'
                )
            """
            )
            exists = await cur.fetchone()
            if exists is not None:
                return exists
            else:
                return False

    async def __create_schema(self, conn: AsyncConnection, schema_name: LiteralString):
        self.logger.info(f"Schema {schema_name} was missing. Creating it now...")
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                CREATE SCHEMA {schema_name}
            """
            )

    async def __create_all_tables(self, conn: AsyncConnection):
        """
        All tables (except for the jobs table, see its creation function) need to created at the same time because of foreign key constraints
        Nothing references the metadata table however we cannot support tables existing without it because the application gets the used schema version from the metadata table
        """
        async with conn.cursor() as cur:
            self.logger.info("Creating metadata table...")
            await cur.execute(
                f"""
                CREATE TABLE {self.schema}.metadata (
                    topic text,
                    data jsonb NOT NULL,
                    PRIMARY KEY (topic)
                )
            """
            )
            # also init all used topics in table so that they are always defined
            application_metadata = {
                "last_used_version": version,
                "last_used_version_tuple": version_tuple,
            }
            await cur.execute(
                f"""
                INSERT INTO {self.schema}.metadata (topic, data)
                VALUES ('application', %s)
            """,
                [Jsonb(application_metadata)],
            )
            cleanup_metadata = {
                "jobs_last_cleanup": datetime.min.isoformat(),
                "users_last_cleanup": datetime.min.isoformat(),
                "runners_last_cleanup": datetime.min.isoformat(),
                "runners_last_cleanup": datetime.min.isoformat(),
            }
            await cur.execute(
                f"""
                INSERT INTO {self.schema}.metadata (topic, data)
                VALUES ('cleanup', %s)
            """,
                [Jsonb(cleanup_metadata)],
            )

            self.logger.info("Creating users table...")
            await cur.execute(
                f"""
                CREATE TABLE {self.schema}.users (
                    id int GENERATED ALWAYS AS IDENTITY,
                    primary key (id)
                )
            """
            )

            self.logger.info("Creating token_secrets table...")
            await cur.execute(
                f"""
                CREATE TABLE {self.schema}.token_secrets (
                    id int GENERATED ALWAYS AS IDENTITY,
                    name varchar(64) NOT NULL,
                    user_id int NOT NULL,
                    secret char(32) NOT NULL DEFAULT MD5(random()::text),
                    temp_token_secret boolean NOT NULL DEFAULT false,
                    PRIMARY KEY (id),
                    FOREIGN KEY (user_id) REFERENCES {self.schema}.users (id) ON DELETE CASCADE
                )
            """
            )
            # make sure that only one token secret can be the temp_token_secret
            await cur.execute(
                f"""
                CREATE UNIQUE INDEX only_one_temp_token_secret_per_user
                ON {self.schema}.token_secrets (user_id)
                WHERE temp_token_secret
                """
            )
            # make sure that there will always be exactly one temp_token_secret by generating a new one at deletion
            await cur.execute(
                f"""
                CREATE OR REPLACE FUNCTION rotatesecret() RETURNS TRIGGER AS $$
                BEGIN
                    INSERT INTO {self.schema}.token_secrets (name, user_id, temp_token_secret)
                    VALUES ('Temporary sessions', OLD.user_id, true);
                    RETURN NULL;
                END;
                $$ LANGUAGE plpgsql
                """
            )
            await cur.execute(
                f"""
                CREATE TRIGGER rotate_temp_token_secret
                AFTER DELETE ON {self.schema}.token_secrets
                FOR EACH ROW
                WHEN (OLD.temp_token_secret)
                EXECUTE FUNCTION rotatesecret()
                """
            )

            self.logger.info("Creating local_accounts table...")
            # according to https://www.rfc-editor.org/errata/eid1003 the upper limit for mail address forward paths is 256 octets (2 of which are angle brackets and thus not part of the address itself). When using UTF-8 this might translate in even less characters, but is still a good upper limit
            await cur.execute(
                f"""
                CREATE TABLE {self.schema}.local_accounts (
                    email varchar(254) NOT NULL,
                    id int NOT NULL UNIQUE,
                    password_hash char(97) NOT NULL,
                    is_admin boolean NOT NULL DEFAULT false,
                    is_verified boolean NOT NULL DEFAULT false,
                    provision_number int UNIQUE DEFAULT null,
                    PRIMARY KEY (email),
                    FOREIGN KEY (id) REFERENCES {self.schema}.users (id) ON DELETE CASCADE
                )
            """
            )

            self.logger.info("Creating oidc_accounts table...")
            await cur.execute(
                f"""
                CREATE TABLE {self.schema}.oidc_accounts (
                    iss text NOT NULL,
                    sub text NOT NULL,
                    id int NOT NULL UNIQUE,
                    email varchar(254) NOT NULL,
                    PRIMARY KEY (iss, sub),
                    FOREIGN KEY (id) REFERENCES {self.schema}.users (id) ON DELETE CASCADE
                )
            """
            )

            self.logger.info("Creating ldap_accounts table...")
            await cur.execute(
                f"""
                CREATE TABLE {self.schema}.ldap_accounts (
                    provider_name text NOT NULL,
                    dn text NOT NULL,
                    id int NOT NULL UNIQUE,
                    email varchar(254) NOT NULL,
                    PRIMARY KEY (provider_name, dn),
                    FOREIGN KEY (id) REFERENCES {self.schema}.users (id) ON DELETE CASCADE
                )
            """
            )

            self.logger.info("Creating runners table...")
            await cur.execute(
                f"""
                CREATE TABLE {self.schema}.runners (
                    id int GENERATED ALWAYS AS IDENTITY,
                    token_hash char(43) UNIQUE,
                    PRIMARY KEY (id)
                )
            """
            )

            self.logger.info("Creating job_settings table...")
            await cur.execute(
                f"""
                CREATE TABLE {self.schema}.job_settings (
                    id int GENERATED ALWAYS AS IDENTITY,
                    user_id int NOT NULL,
                    is_default bool NOT NULL DEFAULT false,
                    settings jsonb NOT NULL,

                    PRIMARY KEY (id),
                    FOREIGN KEY (user_id) REFERENCES {self.schema}.users (id) ON DELETE CASCADE
                )
                """
            )
            # make sure that there can only be one setting set as default per user
            await cur.execute(
                f"""
                CREATE UNIQUE INDEX only_one_default_setting_per_user
                ON {self.schema}.job_settings (user_id)
                WHERE is_default
                """
            )

            self.logger.info("Creating jobs table")
            await cur.execute(
                f"""
                CREATE TABLE {self.schema}.jobs (
                    id int GENERATED ALWAYS AS IDENTITY,
                    user_id int NOT NULL,
                    job_settings_id int,
                    creation_timestamp timestamptz NOT NULL DEFAULT now(),
                    file_name text NOT NULL,
                    audio_oid oid,
                    finish_timestamp timestamptz,
                    runner_name varchar(40),
                    runner_id int,
                    runner_version text,
                    runner_git_hash char(40),
                    runner_source_code_url text,
                    downloaded boolean,
                    error_msg text,
                    PRIMARY KEY (id),
                    FOREIGN KEY (user_id) REFERENCES {self.schema}.users (id) ON DELETE CASCADE,
                    FOREIGN KEY (job_settings_id) REFERENCES {self.schema}.job_settings (id) ON DELETE CASCADE,
                    FOREIGN KEY (runner_id) REFERENCES {self.schema}.runners (id) ON DELETE SET NULL,
                    CONSTRAINT only_finished_job_can_have_runner CHECK (
                        (finish_timestamp IS NULL AND runner_id IS NULL AND runner_name IS NULL AND runner_version IS NULL AND runner_git_hash IS NULL AND runner_source_code_url IS NULL)
                        OR finish_timestamp IS NOT NULL
                    ),
                    CONSTRAINT either_no_or_all_runner_info CHECK (
                        (runner_id IS NULL AND runner_name IS NULL AND runner_version IS NULL AND runner_git_hash IS NULL AND runner_source_code_url IS NULL)
                        OR (runner_id IS NOT NULL AND runner_name IS NOT NULL AND runner_version IS NOT NULL AND runner_git_hash IS NOT NULL AND runner_source_code_url IS NOT NULL)
                    ),
                    CONSTRAINT only_finished_job_is_succeeded_or_failed CHECK (
                        (finish_timestamp IS NOT NULL AND downloaded IS NOT NULL AND error_msg IS NULL)
                        OR (finish_timestamp IS NOT NULL AND downloaded IS NULL AND error_msg IS NOT NULL)
                        OR (finish_timestamp IS NULL AND downloaded IS NULL AND error_msg IS NULL)
                    ),
                    CONSTRAINT only_running_job_has_audio_oidc CHECK (
                        (finish_timestamp IS NULL AND audio_oid IS NOT NULL)
                        OR (finish_timestamp IS NOT NULL AND audio_oid IS NULL)
                    )
                )
            """
            )
            # user_id is neither primary key nor unique, so we have to create an index for it manually.
            # this makes sense since queries where we want to get jobs of a user are very common, and because else the ON DELETE CASCADE would be very expensive
            await cur.execute(
                f"""
                CREATE INDEX ON {self.schema}.jobs (user_id)
            """
            )

            self.logger.info("Creating transcripts table")
            await cur.execute(
                f"""
                CREATE TABLE {self.schema}.transcripts (
                    job_id int,
                    as_txt text NOT NULL,
                    as_srt text NOT NULL,
                    as_tsv text NOT NULL,
                    as_vtt text NOT NULL,
                    as_json jsonb NOT NULL,
                    PRIMARY KEY (job_id),
                    FOREIGN KEY (job_id) REFERENCES {self.schema}.jobs (id) ON DELETE CASCADE
                )
                """
            )

    async def __update_database_schema_if_needed(self, conn: AsyncConnection):
        self.logger.info("Checking application version in database metadata...")
        async with conn.cursor(row_factory=scalar_row) as cur:
            # first check if last_used_version is newer than the current version
            # this would mean that another instance of the application (e.g. another Kubernetes pod) is running on a newer version than this one
            # this is common when updating Kubernetes deployments since pods will be taken down and updated one-by-one for zero downtime
            # this of course can only be done if there are no breaking changes in the database with the newer version. This needs to be checked here in the future when we introduce such changes
            await cur.execute(
                f"""
                SELECT data
                FROM {self.schema}.metadata
                WHERE topic = 'application'
            """
            )
            application_metadata = await cur.fetchone()
            if (
                application_metadata is not None
                and (db_version_tuple := application_metadata.get("last_used_version_tuple"))
                is not None
                and (db_version := application_metadata.get("last_used_version")) is not None
            ):
                parsed_version_tuple = parse_version_tuple(version_tuple)
                parsed_db_version_tuple = parse_version_tuple(db_version_tuple)
                if parsed_version_tuple > parsed_db_version_tuple:
                    # TODO: Add database migration code here once it becomes necessary after a future update

                    # update version tuple if this application is newer than previous one after database migration has completed
                    self.logger.info(
                        "Application has been updated. Updating database metadata with new version..."
                    )
                    await cur.execute(
                        f"""
                        UPDATE {self.schema}.metadata
                        SET data = jsonb_set(
                            jsonb_set(
                                data,
                                '{{last_used_version}}',
                                %s
                            ),
                            '{{last_used_version_tuple}}',
                            %s
                        )
                        WHERE topic = 'application'
                    """,
                        (Jsonb(version), Jsonb(version_tuple)),
                    )

                elif parsed_version_tuple < parsed_db_version_tuple:
                    if parsed_version_tuple[0] < parsed_db_version_tuple[0]:
                        # there is another application instance running that runs on a newer major version. Abort!
                        raise Exception(
                            f"The database has been converted to application version {db_version} while this application only runs on version {version}. Downgrading between major versions is not supported!"
                        )

                else:
                    self.logger.info("No database schema migration required")

    async def _add_local_user_hashed(
        self,
        email: EmailValidated,
        hashed_password: str,
        is_admin: bool = False,
        is_verified: bool = False,
    ) -> int | None:
        async with self.apool.connection() as conn:
            async with conn.cursor(row_factory=scalar_row) as cur:
                await cur.execute(
                    f"""
                    SELECT id
                    FROM {self.schema}.local_accounts
                    WHERE email = %s
                """,
                    (email.root,),
                )
                if user_id := await cur.fetchone():
                    return None

                await cur.execute(
                    f"""
                    INSERT INTO {self.schema}.users (id)
                    VALUES (DEFAULT)
                    RETURNING id
                    """,
                )
                if user_id := await cur.fetchone():
                    await cur.execute(
                        f"""
                        INSERT INTO {self.schema}.local_accounts (email, id, password_hash, is_admin, is_verified)
                        VALUES (%s, %s, %s, %s, %s)
                    """,
                        (email.root, user_id, hashed_password, is_admin, is_verified),
                    )
                    await cur.execute(
                        f"""
                        INSERT INTO {self.schema}.token_secrets (name, user_id, temp_token_secret)
                        VALUES ('Temporary sessions', %s, true)
                    """,
                        (user_id,),
                    )
                    return user_id
                else:
                    raise Exception(
                        f"Error occurred while creating local user {email}: No user id returned!"
                    )

    async def _ensure_local_user_is_provisioned_hashed(
        self,
        provision_number: int,
        email: EmailValidated,
        hashed_password: str,
        is_admin: bool = False,
    ) -> int:
        async with self.apool.connection() as conn:
            async with conn.cursor(row_factory=class_row(LocalUserInDb)) as cur:
                await cur.execute(
                    f"""
                    SELECT *
                    FROM {self.schema}.local_accounts
                    WHERE provision_number = %s
                """,
                    (provision_number,),
                )
                if user := await cur.fetchone():
                    await cur.execute(
                        f"""
                            UPDATE {self.schema}.local_accounts
                            SET (email, password_hash, is_admin) = (%s, %s, %s)
                            WHERE id = %s
                        """,
                        (email.root, hashed_password, is_admin, user.id),
                    )
                    return user.id

            async with conn.cursor(row_factory=scalar_row) as cur:
                await cur.execute(
                    f"""
                    INSERT INTO {self.schema}.users (id)
                    VALUES (DEFAULT)
                    RETURNING id
                    """,
                )
                if user_id := await cur.fetchone():
                    await cur.execute(
                        f"""
                        INSERT INTO {self.schema}.local_accounts (email, id, password_hash, is_admin, is_verified, provision_number)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                        (
                            email.root,
                            user_id,
                            hashed_password,
                            is_admin,
                            True,
                            provision_number,
                        ),
                    )
                    await cur.execute(
                        f"""
                        INSERT INTO {self.schema}.token_secrets (name, user_id, temp_token_secret)
                        VALUES ('Temporary sessions', %s, true)
                    """,
                        (user_id,),
                    )
                    return user_id
                else:
                    raise Exception(
                        f"Error occurred while creating local user {email}: No user id returned!"
                    )

    async def ensure_oidc_user_exists(self, iss: str, sub: str, email: EmailValidated) -> int:
        async with self.apool.connection() as conn:
            async with conn.cursor(row_factory=class_row(OidcUserInDb)) as cur:
                await cur.execute(
                    f"""
                    SELECT *
                    FROM {self.schema}.oidc_accounts
                    WHERE iss = %s AND sub = %s
                """,
                    (iss, sub),
                )
                if user := await cur.fetchone():
                    if user.email.root != email:
                        await cur.execute(
                            f"""
                            UPDATE {self.schema}.oidc_accounts
                            SET email = %s
                            WHERE iss = %s AND sub = %s
                            """,
                            (email.root, iss, sub),
                        )
                    return user.id

            async with conn.cursor(row_factory=scalar_row) as cur:
                await cur.execute(
                    f"""
                    INSERT INTO {self.schema}.users (id)
                    VALUES (DEFAULT)
                    RETURNING id
                    """,
                )
                if user_id := await cur.fetchone():
                    await cur.execute(
                        f"""
                        INSERT INTO {self.schema}.oidc_accounts (iss, sub, id, email)
                        VALUES (%s, %s, %s, %s)
                    """,
                        (iss, sub, user_id, email.root),
                    )
                    return user_id
                else:
                    raise Exception(
                        f"Error occurred while creating oidc user {email}: No user id returned!"
                    )

    async def ensure_ldap_user_exists(
        self, provider_name: str, dn: str, email: EmailValidated
    ) -> int:
        async with self.apool.connection() as conn:
            async with conn.cursor(row_factory=class_row(LdapUserInDb)) as cur:
                await cur.execute(
                    f"""
                    SELECT *
                    FROM {self.schema}.ldap_accounts
                    WHERE provider_name = %s AND dn = %s
                """,
                    (provider_name, dn),
                )
                if user := await cur.fetchone():
                    if user.email.root != email:
                        await cur.execute(
                            f"""
                            UPDATE {self.schema}.ldap_accounts
                            SET email = %s
                            WHERE provider_name = %s AND dn = %s
                            """,
                            (email.root, provider_name, dn),
                        )
                    return user.id

            async with conn.cursor(row_factory=scalar_row) as cur:
                await cur.execute(
                    f"""
                    INSERT INTO {self.schema}.users (id)
                    VALUES (DEFAULT)
                    RETURNING id
                    """,
                )
                if user_id := await cur.fetchone():
                    await cur.execute(
                        f"""
                        INSERT INTO {self.schema}.ldap_accounts (provider_name, dn, id, email)
                        VALUES (%s, %s, %s, %s)
                    """,
                        (provider_name, dn, user_id, email.root),
                    )
                    await cur.execute(
                        f"""
                        INSERT INTO {self.schema}.token_secrets (name, user_id, temp_token_secret)
                        VALUES ('Temporary sessions', %s, true)
                    """,
                        (user_id,),
                    )
                    return user_id
                else:
                    raise Exception(
                        f"Error occurred while creating ldap user {email}: No user id returned!"
                    )

    async def get_new_token_for_user(self, user_id: int, name: str) -> TokenSecret:
        async with self.apool.connection() as conn:
            async with conn.cursor(row_factory=class_row(TokenSecret)) as cur:
                await cur.execute(
                    f"""
                    INSERT INTO {self.schema}.token_secrets (name, user_id, temp_token_secret)
                    VALUES (%s, %s, false)
                    RETURNING *
                    """,
                    (name, user_id),
                )
                token_secret = await cur.fetchone()
                if token_secret is None:
                    raise Exception("Creation of a new token secret failed")
                return token_secret

    async def delete_user(self, user_id):
        async with self.apool.connection() as conn:
            async with conn.cursor() as cur:
                # jobs of that user get automatically deleted because of the 'ON DELETE CASCADE' specified during table creation
                await cur.execute(
                    f"""
                        DELETE FROM {self.schema}.users
                        WHERE id = %s
                    """,
                    (user_id,),
                )

    async def delete_token_secret_of_user(self, user_id: int, token_id: int):
        async with self.apool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    f"""
                        DELETE FROM {self.schema}.token_secrets
                        WHERE id = %s AND user_id = %s
                    """,
                    (token_id, user_id),
                )

    async def delete_all_token_secrets_of_user(self, user_id: int):
        async with self.apool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    f"""
                        DELETE FROM {self.schema}.token_secrets
                        WHERE user_id = %s
                    """,
                    (user_id,),
                )

    async def delete_jobs_of_user(self, user_id: int, job_ids: list[int]):
        async with self.apool.connection() as conn:
            async with conn.cursor(row_factory=scalar_row) as cur:
                await cur.execute(
                    f"""
                        DELETE FROM {self.schema}.jobs
                        WHERE user_id = %s
                        AND id = ANY(%s)
                        RETURNING job_settings_id
                    """,
                    (user_id, job_ids),
                )
                job_setting_ids = await cur.fetchall()

                # also cleanup job_settings table, but only if no other job references the same job setting anymore and it isn't the default
                await cur.execute(
                    f"""
                        DELETE FROM {self.schema}.job_settings settings
                        WHERE settings.id = ANY(%s)
                        AND settings.is_default = false
                        AND NOT EXISTS (
                            SELECT *
                            FROM {self.schema}.jobs jobs
                            WHERE jobs.job_settings_id = settings.id
                        )
                    """,
                    (job_setting_ids,),
                )

    async def get_local_user_by_email(self, email: EmailValidated) -> LocalUserInDb | None:
        async with self.apool.connection() as conn:
            async with conn.cursor(row_factory=class_row(LocalUserInDb)) as cur:
                await cur.execute(
                    f"""
                    SELECT *
                    FROM {self.schema}.local_accounts
                    WHERE email = %s
                """,
                    (email.root,),
                )
                return await cur.fetchone()

    async def get_oidc_user_by_iss_sub(self, iss: str, sub: str) -> OidcUserInDb | None:
        async with self.apool.connection() as conn:
            async with conn.cursor(row_factory=class_row(OidcUserInDb)) as cur:
                await cur.execute(
                    f"""
                        SELECT *
                        FROM {self.schema}.oidc_accounts
                        WHERE iss = %s AND sub = %s
                    """,
                    (iss, sub),
                )
                return await cur.fetchone()

    async def get_ldap_user_by_id(self, user_id: int) -> LdapUserInDb | None:
        async with self.apool.connection() as conn:
            async with conn.cursor(row_factory=class_row(LdapUserInDb)) as cur:
                await cur.execute(
                    f"""
                        SELECT *
                        FROM {self.schema}.ldap_accounts
                        WHERE id = %s
                    """,
                    (str(user_id),),
                )
                return await cur.fetchone()

    async def get_token_secret_of_user(self, user_id: int, token_id: int) -> TokenSecret | None:
        async with self.apool.connection() as conn:
            async with conn.cursor(row_factory=class_row(TokenSecret)) as cur:
                await cur.execute(
                    f"""
                        SELECT *
                        FROM {self.schema}.token_secrets
                        WHERE id = %s AND user_id = %s
                    """,
                    (str(token_id), str(user_id)),
                )
                return await cur.fetchone()

    async def get_temp_session_token_secret_of_user(self, user_id: int) -> TokenSecret | None:
        async with self.apool.connection() as conn:
            async with conn.cursor(row_factory=class_row(TokenSecret)) as cur:
                await cur.execute(
                    f"""
                        SELECT *
                        FROM {self.schema}.token_secrets
                        WHERE user_id = %s AND temp_token_secret = true
                    """,
                    (str(user_id),),
                )
                return await cur.fetchone()

    async def get_info_of_all_tokens_of_user(self, user_id: int) -> list[TokenSecretInfo]:
        async with self.apool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    f"""
                        SELECT (id, name, temp_token_secret)
                        FROM {self.schema}.token_secrets
                        WHERE user_id = %s
                    """,
                    (str(user_id),),
                )
                rows = []
                for row_tup in await cur.fetchall():
                    row = row_tup[0]
                    rows.append(TokenSecretInfo(id=row[0], name=row[1], temp_token_secret=row[2]))
                return rows

    async def _update_password_hash(self, user_id: int, new_password_hash: str):
        async with self.apool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    f"""
                        UPDATE {self.schema}.local_accounts
                        SET password_hash = %s
                        WHERE id = %s
                    """,
                    (new_password_hash, user_id),
                )

    async def verify_local_user(self, user_id: int, new_email: EmailValidated):
        async with self.apool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    f"""
                        UPDATE {self.schema}.local_accounts
                        SET (email, is_verified) = (%s, true)
                        WHERE id = %s
                    """,
                    (new_email.root, user_id),
                )

    async def _update_local_user_password(
        self, email: EmailValidated, hashed_new_password: str
    ) -> int | None:
        async with self.apool.connection() as conn:
            async with conn.cursor(row_factory=scalar_row) as cur:
                await cur.execute(
                    f"""
                        UPDATE {self.schema}.local_accounts
                        SET password_hash = %s
                        WHERE email = %s
                        RETURNING id
                    """,
                    (hashed_new_password, email.root),
                )
                return await cur.fetchone()

    async def _create_runner_hashed(self, token_hash: str) -> int:
        async with self.apool.connection() as conn:
            async with conn.cursor(row_factory=scalar_row) as cur:
                await cur.execute(
                    f"""
                        INSERT INTO {self.schema}.runners (token_hash)
                        VALUES (%s)
                        RETURNING id
                    """,
                    (token_hash,),
                )

                if not (runner_id := await cur.fetchone()):
                    raise Exception("Database didn't return runner ID after inserting new runner")
                else:
                    return runner_id

    async def _get_runner_by_token_hashed(self, token_hash: str) -> int | None:
        async with self.apool.connection() as conn:
            async with conn.cursor(row_factory=class_row(RunnerInDb)) as cur:
                await cur.execute(
                    f"""
                        SELECT *
                        FROM {self.schema}.runners
                        WHERE token_hash = %s
                    """,
                    (token_hash,),
                )

                if not (runner := await cur.fetchone()):
                    return None
                else:
                    return runner.id

    async def add_new_job_settings(
        self, user_id: int, job_settings: JobSettings, is_new_default: bool = False
    ) -> int:
        async with self.apool.connection() as conn:
            async with conn.cursor(row_factory=scalar_row) as cur:
                if is_new_default:  # first set the old settings to not be the default anymore
                    await cur.execute(
                        f"""
                            UPDATE {self.schema}.job_settings
                            SET is_default = false
                            WHERE user_id = %s AND is_default = true
                        """,
                        (user_id,),
                    )
                await cur.execute(
                    f"""
                        INSERT INTO {self.schema}.job_settings (user_id, is_default, settings)
                        VALUES (%s, %s, %s)
                        RETURNING id
                    """,
                    (user_id, is_new_default, Jsonb(job_settings.model_dump())),
                )
                if job_settings_id := await cur.fetchone():
                    return job_settings_id
                else:
                    raise Exception("Didn't return id of new job_settings")

    async def get_default_job_settings_of_user(self, user_id: int) -> JobSettings | None:
        async with self.apool.connection() as conn:
            async with conn.cursor(row_factory=class_row(JobSettingsInDb)) as cur:
                await cur.execute(
                    f"""
                        SELECT settings
                        FROM {self.schema}.job_settings
                        WHERE user_id = %s AND is_default = true
                    """,
                    (user_id,),
                )
                if (entry := await cur.fetchone()) is None:
                    return None
                else:
                    return entry.settings

    async def get_job_settings_by_job_id(self, job_id: int) -> JobSettings | None:
        async with self.apool.connection() as conn:
            # first check if job uses application wide default settings
            async with conn.cursor(row_factory=scalar_row) as cur:
                await cur.execute(
                    f"""
                        SELECT job_settings_id IS NULL
                        FROM {self.schema}.jobs
                        WHERE id = %s
                    """,
                    (job_id,),
                )
                if await cur.fetchone():
                    return JobSettings()

            async with conn.cursor(row_factory=class_row(JobSettingsInDb)) as cur:
                await cur.execute(
                    f"""
                        SELECT settings.settings
                        FROM {self.schema}.job_settings settings, {self.schema}.jobs job
                        WHERE job.id = %s AND job.job_settings_id = settings.id
                    """,
                    (job_id,),
                )
                if (entry := await cur.fetchone()) is None:
                    return None
                else:
                    return entry.settings

    async def add_new_job(
        self, user_id: int, audio_file: UploadFile, job_settings_id: int | None = None
    ) -> int | None:
        async with self.apool.connection() as conn:
            if job_settings_id is None:
                async with conn.cursor(row_factory=scalar_row) as cur:
                    await cur.execute(
                        f"""
                                SELECT id
                                FROM {self.schema}.job_settings
                                WHERE user_id = %s AND is_default = true
                            """,
                        (user_id,),
                    )
                    job_settings_id = await cur.fetchone()
            else:
                async with conn.cursor(row_factory=class_row(JobSettingsInDb)) as cur:
                    await cur.execute(
                        f"""
                            SELECT settings
                            FROM {self.schema}.job_settings
                            WHERE user_id = %s AND id = %s
                        """,
                        (user_id, job_settings_id),
                    )
                    if await cur.fetchone() is None:
                        return None
            async with conn.cursor(row_factory=scalar_row) as cur:
                await cur.execute(
                    f"""
                        SELECT lo_creat(-1)
                    """
                )
                oid = await cur.fetchone()
                offset = 0
                while chunk := await audio_file.read(self.__file_chunk_size_in_bytes):
                    await cur.execute(
                        f"""
                            SELECT lo_put(%s, %s, %s)
                        """,
                        (oid, offset, chunk),
                    )
                    offset += self.__file_chunk_size_in_bytes
                await cur.execute(
                    f"""
                        INSERT INTO {self.schema}.jobs (user_id, job_settings_id, file_name, audio_oid)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                    """,
                    (user_id, job_settings_id, audio_file.filename, oid),
                )
                if job_id := await cur.fetchone():
                    return job_id
                else:
                    raise Exception("Didn't return id of new job")

    async def get_total_number_of_jobs_of_user(
        self, user_id: int, excl_finished: bool, excl_downloaded: bool
    ) -> int:
        if excl_finished:
            additional_and = "AND finish_timestamp IS NULL"
        elif excl_downloaded:
            additional_and = "AND (downloaded IS NULL OR downloaded = false)"
        else:
            additional_and = ""
        async with self.apool.connection() as conn:
            async with conn.cursor(row_factory=scalar_row) as cur:
                await cur.execute(
                    f"""
                        SELECT count(*)
                        FROM {self.schema}.jobs
                        WHERE user_id = %s
                        {additional_and}
                    """,
                    (user_id,),
                )
                if (count := await cur.fetchone()) is None:
                    raise Exception(f"Couldn't get job count of user {user_id}!")
                return count

    async def get_top_k_job_ids_of_user(
        self,
        user_id: int,
        k: int,
        sort_key: JobSortKey,
        desc: bool,
        excl_finished: bool,
        excl_downloaded: bool,
    ) -> list[int]:
        if excl_finished:
            additional_and = "AND finish_timestamp IS NULL"
        elif excl_downloaded:
            additional_and = "AND (downloaded IS NULL OR downloaded = false)"
        else:
            additional_and = ""
        if sort_key == JobSortKey.CREATION_TIME:
            sort_col = "creation_timestamp"
        elif sort_key == JobSortKey.FILENAME:
            sort_col = "file_name"
        if desc:
            comparison_op = (
                "<="  # bigger jobs (left) have less jobs which are larger than it (right)
            )
        else:
            comparison_op = (
                ">="  # bigger jobs (left) have more jobs which are smaller than it (right)
            )
        async with self.apool.connection() as conn:
            async with conn.cursor(row_factory=scalar_row) as cur:
                await cur.execute(
                    f"""
                    WITH filtered_jobs AS (
                        SELECT *
                        FROM {self.schema}.jobs
                        WHERE user_id = %s
                        {additional_and})
                    SELECT j1.id
                    FROM filtered_jobs j1, filtered_jobs j2
                    WHERE j1.{sort_col} {comparison_op} j2.{sort_col}
                    GROUP BY j1.id
                    HAVING count(*) <= %s
                    ORDER BY count(*)
                    """,
                    (user_id, k),
                )
                return await cur.fetchall()

    async def get_job_infos_of_user(self, user_id: int, job_ids: list[int]) -> list[JobBase]:
        async with self.apool.connection() as conn:
            async with conn.cursor(row_factory=class_row(JobBase)) as cur:
                await cur.execute(
                    f"""
                        SELECT *
                        FROM {self.schema}.jobs
                        WHERE user_id = %s
                        AND id = ANY(%s)
                    """,
                    (user_id, job_ids),
                )
                return await cur.fetchall()

    async def get_job_infos_with_settings_of_user(
        self, user_id: int, job_ids: list[int]
    ) -> list[JobAndSettings]:
        jobs = []
        async with self.apool.connection() as conn:
            async with conn.cursor(row_factory=class_row(JobAndSettings)) as cur:
                # first query jobs that use application wide default settings
                await cur.execute(
                    f"""
                        SELECT *
                        FROM {self.schema}.jobs
                        WHERE job_settings_id IS NULL
                        AND id = ANY(%s)
                    """,
                    (job_ids,),
                )
                jobs += await cur.fetchall()

                await cur.execute(
                    f"""
                        SELECT job.*, settings.settings
                        FROM {self.schema}.job_settings settings, {self.schema}.jobs job
                        WHERE job.job_settings_id = settings.id
                        AND job.user_id = %s
                        AND job.id = ANY(%s)
                    """,
                    (user_id, job_ids),
                )
                jobs += await cur.fetchall()
                return jobs

    async def get_job_audio(self, job_id: int) -> AsyncGenerator[bytes, None]:
        async with self.apool.connection() as conn:
            async with conn.cursor(row_factory=scalar_row) as cur:
                await cur.execute(
                    f"""
                        SELECT audio_oid
                        FROM {self.schema}.jobs
                        WHERE id = %s
                    """,
                    (job_id,),
                )
                if (audio_oid := await cur.fetchone()) is None:
                    return

                offset = 0
                await cur.execute(
                    f"""
                        SELECT lo_get(%s, %s, %s)
                    """,
                    (audio_oid, offset, self.__file_chunk_size_in_bytes),
                )
                while chunk := await cur.fetchone():
                    yield chunk
                    offset += self.__file_chunk_size_in_bytes
                    await cur.execute(
                        f"""
                            SELECT lo_get(%s, %s, %s)
                        """,
                        (audio_oid, offset, self.__file_chunk_size_in_bytes),
                    )

    async def get_job_transcript_of_user(
        self, user_id: int, job_id: int, transcript_type: TranscriptTypeEnum
    ) -> str | dict | None:
        async with self.apool.connection() as conn:
            async with conn.cursor(row_factory=scalar_row) as cur:
                await cur.execute(
                    f"""
                        SELECT transcript.{transcript_type.value}
                        FROM {self.schema}.transcripts transcript, {self.schema}.jobs job
                        WHERE transcript.job_id = job.id
                        AND job.user_id = %s
                        AND transcript.job_id = %s
                    """,
                    (user_id, job_id),
                )
                return await cur.fetchone()

    async def get_all_ids_of_unfinished_jobs(self) -> list[int]:
        async with self.apool.connection() as conn:
            async with conn.cursor(row_factory=scalar_row) as cur:
                await cur.execute(
                    f"""
                        SELECT id
                        FROM {self.schema}.jobs
                        WHERE finish_timestamp IS NULL
                    """
                )
                return await cur.fetchall()

    async def finish_successful_job(self, runner: OnlineRunner, transcript: Transcript):
        async with self.apool.connection() as conn:
            async with conn.cursor(row_factory=scalar_row) as cur:
                await cur.execute(
                    f"""
                        SELECT audio_oid
                        FROM {self.schema}.jobs
                        WHERE id = %s
                    """,
                    (runner.in_process_job_id,),
                )
                if (audio_oid := await cur.fetchone()) is None:
                    raise Exception(
                        f"Couldn't get audio_oid for the unfinished job with id {runner.in_process_job_id}"
                    )
                await cur.execute(
                    f"""
                        UPDATE {self.schema}.jobs
                        SET (audio_oid, finish_timestamp, downloaded, runner_id, runner_name, runner_version, runner_git_hash, runner_source_code_url) = (NULL, now(), false, %s, %s, %s, %s, %s)
                        WHERE id = %s
                    """,
                    (
                        runner.id,
                        runner.name,
                        runner.version,
                        runner.git_hash,
                        runner.source_code_url,
                        runner.in_process_job_id,
                    ),
                )
                await cur.execute(
                    f"""
                        INSERT INTO {self.schema}.transcripts (job_id, as_txt, as_srt, as_tsv, as_vtt, as_json)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        runner.in_process_job_id,
                        transcript.as_txt,
                        transcript.as_srt,
                        transcript.as_tsv,
                        transcript.as_vtt,
                        Jsonb(transcript.as_json),
                    ),
                )
                await cur.execute(
                    f"""
                        SELECT lo_unlink(%s)
                    """,
                    (audio_oid,),
                )

    async def finish_failed_job(
        self, job_id: int, error_msg: str, runner: OnlineRunner | None = None
    ):
        if runner:
            if runner.assigned_job_id != job_id:
                raise Exception("The provided online runner doesn't fit to the provided job_id!")
            runner_id = runner.id
            runner_name = runner.id
            runner_version = runner.id
            runner_git_hash = runner.git_hash
            runner_source_code_url = runner.source_code_url
        else:
            runner_id = None
            runner_name = None
            runner_version = None
            runner_git_hash = None
            runner_source_code_url = None
        async with self.apool.connection() as conn:
            async with conn.cursor(row_factory=scalar_row) as cur:
                await cur.execute(
                    f"""
                        SELECT audio_oid
                        FROM {self.schema}.jobs
                        WHERE id = %s
                    """,
                    (job_id,),
                )
                if (audio_oid := await cur.fetchone()) is None:
                    raise Exception(
                        f"Couldn't get audio_oid for the unfinished job with id {job_id}"
                    )
                await cur.execute(
                    f"""
                        UPDATE {self.schema}.jobs
                        SET (audio_oid, finish_timestamp, runner_id, runner_name, runner_version, runner_git_hash, runner_source_code_url, error_msg) = (NULL, now(), %s, %s, %s, %s, %s, %s)
                        WHERE id = %s
                    """,
                    (
                        runner_id,
                        runner_name,
                        runner_version,
                        runner_git_hash,
                        runner_source_code_url,
                        error_msg,
                        job_id,
                    ),
                )
                await cur.execute(
                    f"""
                        SELECT lo_unlink(%s)
                    """,
                    (audio_oid,),
                )
