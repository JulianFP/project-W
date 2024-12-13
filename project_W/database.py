import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import LiteralString

from _version import version, version_tuple
from argon2 import PasswordHasher
from logger import get_logger
from psycopg import pq
from psycopg.connection_async import AsyncConnection
from psycopg.rows import class_row, scalar_row
from psycopg.types.json import Jsonb
from psycopg_pool.pool_async import AsyncConnectionPool
from utils import parse_version_tuple


# data classes for the functions below
@dataclass
class User:
    id: int
    email: str
    password_hash: str
    is_admin: bool
    activated: bool


class database_adapter(ABC):
    """
    Important semantics:
    This class is designed to be used together with startup/shutdown hooks of a web framework, specifically the lifespan function in FastAPI
    As such before any other method of this class can be used the open() method should be called and before shutdown the close() method should be called
    many private methods (prefixed with __) do not create or close transactions (since they do not get their own connection). Instead other non-private methods are expected to lend them their connection. This way we can combine the same sql queries in multiple transactions while reusing the same code
    """

    hasher = PasswordHasher()
    logger = get_logger("project-W")

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
    async def _add_new_user_hashed(
        self, email: str, hashed_password: str, is_admin: bool = False, activated: bool = False
    ) -> bool:
        """
        This method creates a new user. The password is already hashed here which is the reason why this method is protected. It should not be used outside of this base class, use add_new_user instead!
        Returns True if successful, False if not (in which case no change has been made to the database since the transaction would have been rolled back)
        """
        pass

    async def add_new_user(
        self, email: str, password: str, is_admin: bool = False, activated: bool = False
    ) -> int:
        """
        Create a new user. The password will be hashed in this function before writing it in the database.
        """
        hashed_password = self.hasher.hash(password)
        return await self._add_new_user_hashed(email, hashed_password, is_admin, activated)

    @abstractmethod
    async def get_user_by_email(self, email: str) -> User | None:
        """
        Return a user with the matching email, or None if the email doesn't match any user
        """
        pass


class postgres_adapter(database_adapter):
    apool = AsyncConnectionPool(
        conninfo="host=/var/run/postgresql dbname=postgres user=postgres",
        open=False,
        check=AsyncConnectionPool.check_connection,
    )  # TODO
    schema: LiteralString = "project_w"
    minimal_required_postgres_version = 14  # for both postgres and libpq

    async def open(self):
        # make sure libpq version is at least the minimal supported one. Do this first because it doesn't even require connecting to the database
        self.__ensure_psycopg_libpq_version()

        await self.apool.open()
        await self.apool.wait()  # this waits until all connections are established. This makes sure that the backend can properly talk to the database before it accepts clients

        async with self.apool.connection() as conn:
            # ensure that the postgresql database version is at least the minimal supported one
            await self.__ensure_postgresql_version(conn)

            if not await self.__check_schema_exists(conn):
                await self.__create_schema(conn)

                # also create all other tables to skip their existence checks and migration code since there can't be any tables in a newly created schema anyway
                await self.__create_metadata_table(conn)
                await self.__create_users_table(conn)
                await self.__create_runners_table(conn)
                await self.__create_jobs_table(conn)
            elif not await self.__check_metadata_table_exists(conn):
                # if the metadata is missing we can't know whether and how to do a migration on the other table. Because of this we throw an exception if the metadata table is missing but any other table exists to be safe
                if await self.__check_users_table_exists(conn):
                    raise Exception(
                        "Critical: The metadata table is missing but the users table still exists. Either restore the metadata table with its previous contents or drop the users table!"
                    )
                if await self.__check_runners_table_exists(conn):
                    raise Exception(
                        "Critical: The metadata table is missing but the runners table still exists. Either restore the metadata table with its previous contents or drop the runners table!"
                    )
                if await self.__check_jobs_table_exists(conn):
                    raise Exception(
                        "Critical: The metadata table is missing but the jobs table still exists. Either restore the metadata table with its previous contents or drop the jobs table!"
                    )

                # if all tables where missing but the schema existed for some reason then ignore that and just create all the tables in that schema
                await self.__create_metadata_table(conn)
                await self.__create_users_table(conn)
                await self.__create_runners_table(conn)
                await self.__create_jobs_table(conn)
            else:
                # if schema and metadata table already existed we still have to check if all the other tables still exist
                # this way the application doesn't get bricked by the sysadmin dropping whole tables to get rid of data
                # do database migration before creating any missing tables because those created tables would have the new format which would brick the migration code
                await self.__update_database_schema_if_needed(conn)

                if not await self.__check_users_table_exists(conn):
                    await self.__create_users_table(conn)
                if not await self.__check_runners_table_exists(conn):
                    await self.__create_runners_table(conn)
                if not await self.__check_jobs_table_exists(conn):
                    await self.__create_jobs_table(conn)

    async def close(self):
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

    def __ensure_psycopg_libpq_version(self):
        version_string = pq.version()
        if int(str(version_string)[0:2]) < self.minimal_required_postgres_version:
            raise Exception(
                f"The version of libpq loaded by psycopg is {version_string} while the minimal required version is {self.minimal_required_postgres_version}"
            )

    async def __check_schema_exists(self, conn: AsyncConnection) -> bool:
        async with conn.cursor(row_factory=scalar_row) as cur:
            await cur.execute(
                f"""
                SELECT EXISTS (
                    SELECT *
                    FROM information_schema.schemata
                    WHERE
                        schema_name = '{self.schema}'
                )
            """
            )
            exists = await cur.fetchone()
            if exists is not None:
                return exists
            else:
                return False

    async def __check_metadata_table_exists(self, conn: AsyncConnection) -> bool:
        async with conn.cursor(row_factory=scalar_row) as cur:
            await cur.execute(
                f"""
                SELECT EXISTS (
                    SELECT *
                    FROM information_schema.tables
                    WHERE
                        table_schema = '{self.schema}' AND
                        table_type = 'BASE TABLE' AND
                        table_name = 'metadata'
                )
            """
            )
            exists = await cur.fetchone()
            if exists is not None:
                return exists
            else:
                return False

    async def __check_users_table_exists(self, conn: AsyncConnection) -> bool:
        async with conn.cursor(row_factory=scalar_row) as cur:
            await cur.execute(
                f"""
                SELECT EXISTS (
                    SELECT *
                    FROM information_schema.tables
                    WHERE
                        table_schema = '{self.schema}' AND
                        table_type = 'BASE TABLE' AND
                        table_name = 'users'
                )
            """
            )
            exists = await cur.fetchone()
            if exists is not None:
                return exists
            else:
                return False

    async def __check_runners_table_exists(self, conn: AsyncConnection) -> bool:
        async with conn.cursor(row_factory=scalar_row) as cur:
            await cur.execute(
                f"""
                SELECT EXISTS (
                    SELECT *
                    FROM information_schema.tables
                    WHERE
                        table_schema = '{self.schema}' AND
                        table_type = 'BASE TABLE' AND
                        table_name = 'runners'
                )
            """
            )
            exists = await cur.fetchone()
            if exists is not None:
                return exists
            else:
                return False

    async def __check_jobs_table_exists(self, conn: AsyncConnection) -> bool:
        async with conn.cursor(row_factory=scalar_row) as cur:
            await cur.execute(
                f"""
                SELECT EXISTS (
                    SELECT *
                    FROM information_schema.tables
                    WHERE
                        table_schema = '{self.schema}' AND
                        table_type = 'BASE TABLE' AND
                        table_name = 'jobs'
                )
            """
            )
            exists = await cur.fetchone()
            if exists is not None:
                return exists
            else:
                return False

    async def __create_schema(self, conn: AsyncConnection):
        self.logger.info("schema was missing. Creating it now...")
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                CREATE SCHEMA {self.schema}
            """
            )

    async def __create_metadata_table(self, conn: AsyncConnection):
        self.logger.info("metadata table was missing. Creating it now...")
        async with conn.cursor() as cur:
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

    async def __create_users_table(self, conn: AsyncConnection):
        self.logger.info("users table was missing. Creating it now...")
        async with conn.cursor() as cur:
            # according to https://www.rfc-editor.org/errata/eid1003 the upper limit for mail address forward paths is 256 octets (2 of which are angle brackets and thus not part of the address itself). When using UTF-8 this might translate in even less characters, but is still a good upper limit
            await cur.execute(
                f"""
                CREATE TABLE {self.schema}.users (
                    id serial,
                    email varchar(254) NOT NULL UNIQUE,
                    password_hash char(97) NOT NULL,
                    is_admin boolean NOT NULL DEFAULT false,
                    activated boolean NOT NULL DEFAULT false,
                    PRIMARY KEY (id)
                )
            """
            )

    async def __create_runners_table(self, conn: AsyncConnection):
        self.logger.info("runners table was missing. Creating it now...")
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                CREATE TABLE {self.schema}.runners (
                    id serial,
                    token_hash char(24) UNIQUE,
                    PRIMARY KEY (id)
                )
            """
            )

    async def __create_jobs_table(self, conn: AsyncConnection):
        self.logger.info("jobs table was missing. Creating it now...")
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
                    runner_id integer,
                    runner_version text,
                    runner_git_hash char(40),
                    runner_source_code_url text,
                    downloaded boolean,
                    transcript text,
                    error_msg text,
                    PRIMARY KEY (id),
                    FOREIGN KEY (user_id) REFERENCES {self.schema}.users (id),
                    FOREIGN KEY (runner_id) REFERENCES {self.schema}.runners (id),
                    CONSTRAINT only_finished_job_has_runner CHECK (
                        (finish_timestamp IS NOT NULL AND runner_id IS NOT NULL AND runner_version IS NOT NULL AND runner_git_hash IS NOT NULL AND runner_source_code_url IS NOT NULL)
                        OR (finish_timestamp IS NULL AND runner_id IS NULL AND runner_version IS NULL AND runner_git_hash IS NULL AND runner_source_code_url IS NULL)
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
            # this makes sense since queries where we want to get jobs of a user are very common
            await cur.execute(
                f"""
                CREATE INDEX ON {self.schema}.jobs (user_id)
            """
            )

    async def _add_new_user_hashed(
        self, email: str, hashed_password: str, is_admin: bool = False, activated: bool = False
    ) -> bool:
        async with self.apool.connection() as conn:
            async with conn.cursor(row_factory=scalar_row) as cur:
                await cur.execute(
                    f"""
                    SELECT EXISTS (
                        SELECT *
                        FROM {self.schema}.users
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
                    INSERT INTO {self.schema}.users (email, password_hash, is_admin, activated)
                    VALUES (%s, %s, %s, %s)
                """,
                    (email, hashed_password, is_admin, activated),
                )
        return True

    async def get_user_by_email(self, email: str) -> User | None:
        async with self.apool.connection() as conn:
            async with conn.cursor(row_factory=class_row(User)) as cur:
                await cur.execute(
                    f"""
                    SELECT *
                    FROM {self.schema}.users
                    WHERE email = %s
                """,
                    (email,),
                )
                return await cur.fetchone()


async def test_database_conn():
    db_conn = postgres_adapter()
    try:
        await db_conn.open()
        result = await db_conn.add_new_user("julian@partanengroup.de", "password1234")
        if not result:
            print(f"failed to create user")
        my_user = await db_conn.get_user_by_email("julian@partanengroup.de")
        if my_user:
            print(f"Succeeded, my user has id {my_user.id}")
    finally:
        await db_conn.close()


asyncio.run(test_database_conn())
