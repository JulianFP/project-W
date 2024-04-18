Connect a runner with the backend
=================================

This page contains a manual for how to connect a runner with its backend, or in other words: How to get a token for a runner.

Give admin rights to a user
---------------------------

Currently only users that have administration rights are allowed to create new runners for the Backend.

.. warning::
   Do not just make any user an admin! Make sure that the admin user has a strong password! Admin users can view all data of all users and do scary stuff like delete any user account. It would be quite bad if an admin user got compromised.

Unfortunately the only way to currently do this is to directly set the correct value in the sqlite database. Here is a step-by-step guide for how to do this:

1. Make sure that you are in the same directory as the ``database.db`` file of the Backend. If you are not sure where it is then refer to the `databasePath` value in the :ref:`description_backend_config-label`.
2. Enter the sql shell of the sqlite database:

   .. code-block:: console
   
      sqlite3 database.db

3. Set ``is_admin`` attribute of the user you want to make an admin to `true` (make sure to replace <users email> with the email address of this user):

   .. code-block:: sql

      UPDATE users
      SET is_admin=1
      WHERE email='<users email>';

4. Print whole table and check if change was successful:

   .. code-block:: sql

      SELECT * FROM users;

   The entry of the second column from the right should be `1` and not `0` for your user (and only your user!)

5. Exit the sqlite shell:

   .. code-block:: sql

      .quit

The desired user should be an admin now!

.. _get_a_runner_token-label:

Get a new runner token
----------------------

To operate a runner you need a token for it. The runner uses it to authenticate with the backend. Without one, the runner won't even start. To get one, you need to call the /api/runners/create route, which will create a new runner in the backend and return its token. For more details about that, please refer to :doc:`api`. After that, you will need to save that token for yourself. If you loose it, then you will have to create a new runner again!

.. warning::
   Please make sure to save the runner token in a secret way! If it gets leaked, anyone could authenticate as that runner and accept and read users jobs in behalf of your runner! If you accidentally leaked a token, immediately revoke that token. Refer to :ref:`revoke_a_runner-label` for that.

Follow the following step-by-step guide to register a new runner. Note that you need to authenticate with an admin user for that. We assume that you are in a Bash Terminal with curl installed:

1. Log in as an admin user by requesting a JWT Token (remember to replace the <placeholders>):

   .. code-block:: console

      curl -X POST -F "email=<email of the admin user>" -F "password=<password of the admin user>" https://<domain of the backend>/api/users/login

   This should return a json object containing the attributes ``msg`` and ``accessToken``. The ``msg`` should say `Login successful`. Please copy the value of ``accessToken``.

2. Store the JWT Token in an environment variable for easy access in subsequent commands:

   .. code-block:: console

      JWT="<value of the accessToken field returned by previous command>"

3. Create the new runner:

   .. code-block:: console

      curl -X GET -H "Authorization: Bearer $JWT" https://<domain of the backend>/api/runners/create

   This should return a json object containing the attribute ``runnerToken``. This is the runner Token you need!

4. Use this runner token for the ``runnerToken`` field of the runners config. Preferably use an environment variable for that. Refer to :ref:`description_runner_config-label`.

.. _revoke_a_runner-label:

Revoke a runner token
---------------------

If a runner token got leaked or if you just don't use this runner anymore and want to clean up, then follow this step-by-step guide:

1. Make sure that you are in the same directory as the ``database.db`` file of the Backend. If you are not sure where it is then refer to the `databasePath` value in the :ref:`description_backend_config-label`.
2. Enter the sql shell of the sqlite database:

   .. code-block:: console
   
      sqlite3 database.db

3. Delete the runner from the table. Make sure to replace <runners id> by the id of the runner from which you want to revoke the token. Runner IDs are created sequentially, so the first runner you created will have ID 1, the second ID 2 and so on:

   .. code-block:: sql
   
      DELETE FROM runners WHERE id=<runners id>;

4. Print whole table and check if change was successful:

   .. code-block:: sql

      SELECT * FROM runners;

   The runner with the id you used above should be gone (and only that runner!).

5. Exit the sqlite shell:

   .. code-block:: sql

      .quit

The runner is now removed and the token is therefore now revoked. Next you probably want to recreate that runner to get a new Token. Refer to :ref:`get_a_runner_token-label` for how to do that.
