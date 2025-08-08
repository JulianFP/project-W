Database encryption
===================

The most sensitive data Project-W handles is only being stored encrypted in the database. This includes audio files, transcripts and oidc refresh tokens. The encryption key being used is the ``secret_key`` supplied through the YAML config file (or the environment variable defined in the config file). Since additionally user passwords and all kinds of access tokens are only stored hashed, a database leak will thus not give a malicious actor any kind of access to audio files or transcripts of your users (as long as to the ``secret_key`` wasn't leaked to them as well).

   .. warning::

      While the most sensitive data like audio and transcripts are encrypted the database still contains unencrypted user-related data like email addresses, file names of the audio files, job settings, and other metadata. You should still very much protect your database and database dumps/backups, by i.e. encrypting your backups yourself!

Rotating the secret_key
-----------------------

You might want to rotate the ``secret_key`` for various reasons, e.g. if it got leaked by accident or the system storing it got compromised. Project-W provides an easy way to do this and re-encrypt all existing database contents with a new secret key ensuring that your users can continue using your instance with minimal disruption:

1. Generate a new secret key. Don't replace it in the config file/env var yet!

   .. code-block:: console

      python -c 'import secrets; print(secrets.token_hex(32))'

2. Shutdown the backend (e.g. the project-w docker container). The secret_key shouldn't be rotated while users still use the instance at the same time.

3. If you are using docker: Enter the project-w_cron container (or the project-w container, but we shut that one down in the previous step). If not, gain access to to the project_w package (the same package running the backend).

   .. code-block:: console

      docker exec -it project-w-project-w_cron-1 /bin/bash

4. Execute the following command. For this the old secret key must still be present in the config file/environment variable:

   .. code-block:: console

      project_W --rotate_secret_key <the new secret key>

5. Replace the secret key in the config file/environment variable with the new one

6. Start the backend again. Both existing and new database content is now encrypted with the new secret key.

If you lost your secret_key
---------------------------

If you lost your ``secret_key`` then there is no way to recover the encrypted contents of the database anymore, this data will be lost indefinitely. If you were to start the backend without providing it the correct secret key for an existing database then it would throw errors left and right once users would try to download their transcripts, use some of their auth tokens or runners would try to process existing unfinished jobs. For this scenario Project-W provides a way to get a working database again (without completely deleting the whole database). Please note however that this method still deletes all encrypted contents of the database and everything that depends on that, i.e. all jobs, transcripts and OIDC auth tokens. This is still very disruptive for your users, but at least they will retain their accounts, account settings, and in case of local and ldap users their auth tokens, and also runner tokens will stay valid.

1. Shutdown the backend (e.g. the project-w docker container). The following shouldn't be done while users still use the instance at the same time.

2. If you are using docker: Enter the project-w_cron container (or the project-w container, but we shut that one down in the previous step). If not, gain access to to the project_w package (the same package running the backend).

   .. code-block:: console

      docker exec -it project-w-project-w_cron-1 /bin/bash

3. Execute the following command:

   .. code-block:: console

      project_W --delete_encrypted_contents_from_database

4. Flush the contents of the Redis database. If you are using docker deleting and re-creating the redis container should do the trick (or if you mounted a volume into the redis container delete the volume). Alternatively use the ``FLUSHALL`` redis command through the redis-cli.

5. Start the backend again. All jobs and oidc auth tokens should be gone now, but it will be in a functioning state again.
