from abc import ABC, abstractmethod
from datetime import datetime
from typing import LiteralString

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from psycopg import pq
from psycopg.connection_async import AsyncConnection
from psycopg.rows import class_row, scalar_row
from psycopg.types.json import Jsonb
from psycopg_pool.pool_async import AsyncConnectionPool

from ._version import version, version_tuple
from .logger import get_logger
from .models.internal import LocalUserInDb, OidcUserInDb
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
    async def _add_new_local_user_hashed(
        self, email: str, hashed_password: str, is_admin: bool = False, is_verified: bool = False
    ) -> bool:
        """
        This method creates a new user. The password is already hashed here which is the reason why this method is protected. It should not be used outside of this base class, use add_new_user instead!
        Returns True if successful, False if not (in which case no change has been made to the database since the transaction would have been rolled back)
        """
        pass

    async def add_new_local_user(
        self, email: str, password: str, is_admin: bool = False, is_verified: bool = False
    ) -> bool:
        """
        Create a new user. The password will be hashed in this function before writing it in the database.
        """
        hashed_password = self.hasher.hash(password)
        return await self._add_new_local_user_hashed(email, hashed_password, is_admin, is_verified)

    @abstractmethod
    async def add_new_oidc_user(self, iss: str, sub: str, email: str) -> bool:
        """
        Add a database entry for an oidc user. Will be called at first login of this user.
        """
        pass

    @abstractmethod
    async def delete_user(self, user_id: int):
        """
        Delete the user with id user_id.
        """
        pass

    @abstractmethod
    async def get_local_user_by_email(self, email: str) -> LocalUserInDb | None:
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
    async def _update_password_hash(self, user_id: int, new_password_hash: str):
        """
        Sometimes passwords need rehashing. This function implements that.
        It gets called every time a password for a user is checked in 'get_user_by_email_checked_password'
        """
        pass

    async def get_local_user_by_email_checked_password(
        self, email: str, password: str
    ) -> LocalUserInDb | None:
        """
        Return a user with the matching email if the provided password is also correct, or None if the email doesn't match any user or the password is incorrect
        Basically 'get_local_user_by_email' with builtin password checker
        """
        user = await self.get_local_user_by_email(email)
        if user is None:
            return None

        try:
            self.hasher.verify(user.password_hash, password)
        except VerificationError:
            return None

        if self.hasher.check_needs_rehash(user.password_hash):
            await self._update_password_hash(user.id, self.hasher.hash(password))

        return user


class PostgresAdapter(DatabaseAdapter):
    apool: AsyncConnectionPool
    schema: LiteralString = "project_w"
    minimal_required_postgres_version = 14  # for both postgres and libpq

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

            if not await self.__check_schema_exists(conn, self.schema):
                await self.__create_schema(conn, self.schema)

                # also create all other tables to skip their existence checks and migration code since there can't be any tables in a newly created schema anyway
                await self.__create_all_tables(conn)
            elif not await self.__check_table_exists(conn, "metadata"):
                # if the metadata is missing we can't know whether and how to do a migration on the other table. Because of this we throw an exception if the metadata table is missing but any other table exists to be safe
                for table_name in "users" "local_accounts" "oidc_accounts" "runners" "jobs":
                    if await self.__check_table_exists(conn, table_name):
                        raise Exception(
                            f"Critical: The metadata table is missing but the {table_name} table still exists. Either restore the metadata table with its previous contents or drop the {table_name} table!"
                        )

                # if all tables where missing but the schema existed for some reason then ignore that and just create all the tables in that schema
                await self.__create_all_tables(conn)
            else:
                # if schema and metadata table already existed we still have to check if all the other tables still exist
                # the only table that is allowed to be dropped on its own is the jobs table, so we throw an error if any of the other tables don't exist
                # do database migration before creating any missing tables because those created tables would have the new format which would brick the migration code
                await self.__update_database_schema_if_needed(conn)

                table_names: list[LiteralString] = [
                    "users",
                    "local_accounts",
                    "oidc_accounts",
                    "runners",
                ]
                for table_name in table_names:
                    if not await self.__check_table_exists(conn, table_name):
                        raise Exception(
                            f"Critical: The metadata table exists but the {table_name} table is missing. Either restore the {table_name} table with its previous contents or drop the metadata table as well!"
                        )
                if not await self.__check_table_exists(conn, "jobs"):
                    await self.__create_jobs_table(conn)

        self.logger.info("Database is ready to use")

    async def close(self):
        self.logger.info("Closing database connections...")
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
                    id serial,
                    PRIMARY KEY (id)
                )
            """
            )

            self.logger.info("Creating local_accounts table...")
            # according to https://www.rfc-editor.org/errata/eid1003 the upper limit for mail address forward paths is 256 octets (2 of which are angle brackets and thus not part of the address itself). When using UTF-8 this might translate in even less characters, but is still a good upper limit
            await cur.execute(
                f"""
                CREATE TABLE {self.schema}.local_accounts (
                    email varchar(254) NOT NULL,
                    id integer NOT NULL,
                    password_hash char(97) NOT NULL,
                    is_admin boolean NOT NULL DEFAULT false,
                    is_verified boolean NOT NULL DEFAULT false,
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
                    id integer NOT NULL,
                    email varchar(254) NOT NULL,
                    PRIMARY KEY (iss, sub),
                    FOREIGN KEY (id) REFERENCES {self.schema}.users (id) ON DELETE CASCADE
                )
            """
            )

            self.logger.info("Creating runners table...")
            await cur.execute(
                f"""
                CREATE TABLE {self.schema}.runners (
                    id serial,
                    token_hash char(24) UNIQUE,
                    PRIMARY KEY (id)
                )
            """
            )

        await self.__create_jobs_table(conn)

    async def __create_jobs_table(self, conn: AsyncConnection):
        """
        Since nothing references the jobs table we allow lazy deletion of all jobs by dropping the whole jobs table.
        This is why it gets its own function.
        """
        self.logger.info("Creating jobs table")
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                CREATE TABLE {self.schema}.jobs (
                    id serial,
                    user_id integer NOT NULL,
                    creation_timestamp timestamp NOT NULL DEFAULT now(),
                    file_name text NOT NULL,
                    model text,
                    language char(2),
                    audio_oid oid,
                    finish_timestamp timestamp,
                    runner_name varchar(40),
                    runner_id integer,
                    runner_version text,
                    runner_git_hash char(40),
                    runner_source_code_url text,
                    downloaded boolean,
                    transcript text,
                    error_msg text,
                    PRIMARY KEY (id),
                    FOREIGN KEY (user_id) REFERENCES {self.schema}.users (id) ON DELETE CASCADE,
                    FOREIGN KEY (runner_id) REFERENCES {self.schema}.runners (id) ON DELETE SET NULL,
                    CONSTRAINT only_finished_job_has_runner CHECK (
                        (finish_timestamp IS NOT NULL AND runner_name IS NOT NULL AND runner_version IS NOT NULL AND runner_git_hash IS NOT NULL AND runner_source_code_url IS NOT NULL)
                        OR (finish_timestamp IS NULL AND runner_id IS NULL AND runner_name IS NULL AND runner_version IS NULL AND runner_git_hash IS NULL AND runner_source_code_url IS NULL)
                    ),
                    CONSTRAINT only_finished_job_is_succeeded_or_failed CHECK (
                        (finish_timestamp IS NOT NULL AND downloaded IS NOT NULL AND transcript IS NOT NULL AND error_msg IS NULL and audio_oid IS NULL)
                        OR (finish_timestamp IS NOT NULL AND error_msg IS NOT NULL AND audio_oid IS NOT NULL AND downloaded IS NULL AND transcript IS NULL)
                        OR (finish_timestamp IS NULL AND downloaded IS NULL AND transcript IS NULL AND error_msg IS NULL)
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

    async def _add_new_local_user_hashed(
        self, email: str, hashed_password: str, is_admin: bool = False, is_verified: bool = False
    ) -> bool:
        async with self.apool.connection() as conn:
            async with conn.cursor(row_factory=scalar_row) as cur:
                await cur.execute(
                    f"""
                    SELECT EXISTS (
                        SELECT *
                        FROM {self.schema}.local_accounts
                        WHERE email = %s
                    )
                """,
                    (email,),
                )
                email_already_in_use: bool | None = await cur.fetchone()
                if email_already_in_use:
                    return False

                await cur.execute(
                    f"""
                    INSERT INTO {self.schema}.users (id)
                    VALUES (DEFAULT)
                    RETURNING id
                    """,
                )
                user_id = await cur.fetchone()
                await cur.execute(
                    f"""
                    INSERT INTO {self.schema}.local_accounts (email, id, password_hash, is_admin, is_verified)
                    VALUES (%s, %s, %s, %s, %s)
                """,
                    (email, user_id, hashed_password, is_admin, is_verified),
                )
        return True

    async def add_new_oidc_user(self, iss: str, sub: str, email: str) -> bool:
        async with self.apool.connection() as conn:
            async with conn.cursor(row_factory=scalar_row) as cur:
                await cur.execute(
                    f"""
                    SELECT EXISTS (
                        SELECT *
                        FROM {self.schema}.oidc_accounts
                        WHERE iss = %s AND sub = %s
                    )
                """,
                    (iss, sub),
                )
                oidc_account_already_exists: bool | None = await cur.fetchone()
                if oidc_account_already_exists:
                    return False

                await cur.execute(
                    f"""
                    INSERT INTO {self.schema}.users (id)
                    VALUES (DEFAULT)
                    RETURNING id
                    """,
                )
                user_id = await cur.fetchone()
                await cur.execute(
                    f"""
                    INSERT INTO {self.schema}.oidc_accounts (iss, sub, id, email)
                    VALUES (%s, %s, %s, %s)
                """,
                    (iss, sub, user_id, email),
                )
        return True

    async def delete_user(self, user_id):
        async with self.apool.connection() as conn:
            async with conn.cursor(row_factory=scalar_row) as cur:
                # jobs of that user get automatically deleted because of the 'ON DELETE CASCADE' specified during table creation
                await cur.execute(
                    f"""
                        DELETE FROM {self.schema}.users
                        WHERE id = %s
                    """,
                    (user_id,),
                )

    async def get_local_user_by_email(self, email: str) -> LocalUserInDb | None:
        async with self.apool.connection() as conn:
            async with conn.cursor(row_factory=class_row(LocalUserInDb)) as cur:
                await cur.execute(
                    f"""
                    SELECT *
                    FROM {self.schema}.local_accounts
                    WHERE email = %s
                """,
                    (email,),
                )
                return_val = await cur.fetchone()
                return LocalUserInDb.model_validate(return_val)

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
                return_val = await cur.fetchone()
                return OidcUserInDb.model_validate(return_val)

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
