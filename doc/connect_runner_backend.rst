Connect a runner with the backend
=================================

This page contains guides about how to login as an admin user with admin privileges and how to use these privileges to create a new runner or to invalidate an existing runner.

.. _login_with_admin_privileges:

Create an admin account and login with admin privileges
-------------------------------------------------------

Currently only users that have administration rights are allowed to create new runners for the Backend.

.. warning::
   Do not just make just any user an admin! Make sure that the admin user has a strong password! Admin users can view all data of all users and do scary stuff like delete any user account. It would be quite bad if an admin user got compromised.

There are three ways to create an user with admin privileges: Through provisioned local accounts, LDAP users that the configured admin_query returns and OIDC users that have the configured admin role. All three methods are controlled through the config file (refer to :ref:`description_backend_config-label`).

Provisioned local accounts
``````````````````````````

This is the easiest method to create an admin user and it doesn't require an external identity provider. Just make sure that your backend's config contains the following section:

.. code-block:: yaml

   security:
     local_account:
       user_provisioning:
         <user provisioning id>:
           email: <user's email>
           password: <user's password>
           is_admin: true

This config will create a local Project-W account with the specified attributes at startup (and also recreate it/ensure that these attributes are still correct, meaning you can also change the email/password/admin privileges of this user through the config at any time). The `<user provisioning id>` can be any integer, for example `0`. Every provisioned user must have a different id though.

If you want that your regular users login through LDAP/OIDC but you still want to use local admin users you can add the following to your config:

.. code-block:: yaml

   security:
     local_account:
       mode: no_signup_hidden

In contrary to the `disabled` mode this will not completely disable local Project-W accounts but just prohibit people to create new local accounts themselves and hide the login option from the frontend. People will still be able to try to login as an existing Project-W account through other means (so the passwords of your provisioned users must still be secure!) but it will not be promoted to them in the main frontend anymore. This is ideal if the only existing local Project-W accounts should be provisioned admin users that normal users shouldn't interact with.

The default login through the frontend as well as API tokens don't have admin privileges by default, even if the user they belong to is an admin user. These privileges must be explicitly requested at login time. To get an authentication token with admin privileges either use the following curl command or perform the same operation on the OpenAPI docs under `/docs` if you prefer a GUI.

.. code-block:: console

   curl -X "POST" "https://<backend url>/api/local-account/login" -d "grant_type=password&scope=admin&username=<user's email>&password=<user's password>"

The important part for requesting admin privileges is the `scope=admin` parameter. This request will of course only be granted if the user is an admin user. Please also remember to URL-escape any special characters in your email and password (e.g. the escape code for '@' is '%40'). We will use the resulting token in the next step.

OIDC admin users
````````````````

add an `admin_role` section to your OIDC provider config:

.. code-block:: yaml

   oidc_providers:
     OIDC Provider:
       icon_url: <url to a svg or png icon>
       base_url: <url to the oidc provider without the /.well-known/.. part>
       client_id: <client id>
       client_secret: <client secret>
       user_role:
         field_name: <oidc claim field name>
         name: <oidc claim required field content for the user to be a normal user>
       admin_role:
         field_name: <oidc claim field name>
         name: <oidc claim required field content for the user to be an admin user>

Now each user that has `name` as configured under `admin_role` in the specified oidc claim is an admin user.

Alternatively if you want to setup a new oidc provider just for admin users then take a look at the following config:

.. code-block:: yaml

   oidc_providers:
     OIDC for normal users:
       icon_url: <url to a svg or png icon>
       base_url: <url to the oidc provider without the /.well-known/.. part>
       client_id: <client id>
       client_secret: <client secret>
       user_role:
         field_name: <oidc claim field name>
         name: <oidc claim required field content for the user to be a normal user>
     OIDC for admin users:
       hidden: true
       base_url: <url to the oidc provider without the /.well-known/.. part>
       client_id: <client id>
       client_secret: <client secret>
       admin_role:
         field_name: <oidc claim field name>
         name: <oidc claim required field content for the user to be an admin user>

The `hidden=true` attribute hides this OIDC provider as a login option from the frontend, similarly how the `no_signup_hidden` option did it for local accounts. Again please note that this is not a security option, users can still try to login through that OIDC provider if they want, so your passwords must remain strong! The OIDC for admin users is just not promoted on the main frontend as a login option.

API token don't have the required admin privileges even if the OIDC user is an admin user. Instead we must use an id\_token returned by the identity provider itself. To get one please login on the main Project-W frontend as your admin OIDC user like you regularly would. Now go into your browser developer options with the `F12` key, navigate to `Application -> Storage -> Local Storage` (Chromium based browsers) or `Storage -> Local Storage` (Firefox based browser). If you are still logged in you should see a key called `authHeader`. Its value is the token we need. Copy it for the next step.

LDAP admin users
````````````````

Add an `admin_query` section to your LDAP provider config:

.. code-block:: yaml

  ldap_providers:
    LDAP Provider:
      icon_url: <url to a svg or png icon>
      server_address: <ldap url>
      service_account_auth:
        user: <service account bind dn>
        password: <service account bind password>
      username_attributes:
         <list of ldap attributes that can be used as a username during login>
      uid_attribute: <ldap attribute contaning unique user identifier>
      mail_attribute: <ldap attribute which contains users mail address>
      user_query:
        base_dn: <base dn under which normal users can be found>
        filter: <ldap filter expression>
      admin_query:
        base_dn: <base dn under which admin users can be found (can be the same as above if filter is different)>
        filter: <ldap filter expression (can be the same as above if base_dn is different)>

Now each user that gets returned by an ldap query under the specified base_dn using the specified filter expression can login as an admin user.

Alternatively if you want to setup a new ldap provider just for admin users then take a look at the following config:

.. code-block:: yaml

   ldap_providers:
     LDAP for regular users:
       icon_url: <url to a svg or png icon>
       server_address: <ldap url>
       service_account_auth:
         user: <service account bind dn>
         password: <service account bind password>
       username_attributes:
         <list of ldap attributes that can be used as a username during login>
       uid_attribute: <ldap attribute contaning unique user identifier>
       mail_attribute: <ldap attribute which contains users mail address>
       user_query:
         base_dn: <base dn under which normal users can be found>
         filter: <ldap filter expression>
     LDAP for admin users:
       hidden: true
       server_address: <ldap url>
       service_account_auth:
         user: <service account bind dn>
         password: <service account bind password>
       username_attributes:
         <list of ldap attributes that can be used as a username during login>
       uid_attribute: <ldap attribute contaning unique user identifier>
       mail_attribute: <ldap attribute which contains users mail address>
       admin_query:
         base_dn: <base dn under which admin users can be found>
         filter: <ldap filter expression>

The `hidden=true` attribute hides this LDAP provider as a login option from the frontend, similarly how the `no_signup_hidden` option did it for local accounts. Again please note that this is not a security option, users can still try to login through that LDAP provider if they want, so your passwords must remain strong! The LDAP for admin users is just not promoted on the main frontend as a login option.

The default login through the frontend as well as API tokens don't have admin privileges by default, even if the user they belong to is an admin user. These privileges must be explicitly requested at login time. To get an authentication token with admin privileges either use the following curl command or perform the same operation on the OpenAPI docs under `/docs` if you prefer a GUI.

.. code-block:: console

   curl -X "POST" "https://<backend url>/api/ldap/login/<ldap provider name from config file>" -d "grant_type=password&scope=admin&username=<ldap username>&password=<ldap password>"

The important part for requesting admin privileges is the `scope=admin` parameter. This request will of course only be granted if the user is an admin user. Please also remember to URL-escape any special characters in your email and password (e.g. the escape code for '@' is '%40', a space must be substituted with '%20'). We will use the resulting token in the next step.

.. _get_a_runner_token-label:

Get a new runner token
----------------------

To operate a runner you need a token for it. The runner uses it to authenticate with the backend. Without one, the runner won't even start. Please note that the runner token is different from the user access tokens (sometimes we also call them JWT tokens) that are being used to authenticate as a user after logging in. For the /api/runners/* routes you need a runner token, for all other authenticated routes you need a user token.

.. warning::
   Please make sure to save the runner token in a secret way! If it gets leaked, anyone could authenticate as that runner and accept and read users jobs in behalf of your runner! If you accidentally leaked a token, immediately revoke that token. Refer to :ref:`revoke_a_runner-label` for that.

Follow the following step-by-step guide to register a new runner. We assume that you are in a Bash Terminal with curl installed:

1. Please login as an admin user with admin privileges. Follow the steps described in :ref:`login_with_admin_privileges` for how to do that.

2. Store the obtained admin user token in an environment variable for easy access in subsequent commands:

   .. code-block:: console

      JWT="<value of the obtained access token>"

2. Create the new runner:

   .. code-block:: console

      curl -X POST -H "Authorization: Bearer $JWT" https://<backend url>/api/admins/create_runner

   This should return a json object containing the attributes ``id`` and ``token``. The latter is the runner token you need!

3. Use this runner token for the ``auth_token`` field under ``backend_settings`` in the runners config. Preferably use an environment variable for that. Refer to :ref:`description_runner_config-label`.

.. _revoke_a_runner-label:

Revoke a runner token
---------------------

If a runner token got leaked or if you just don't use this runner anymore and want to clean up, then follow this step-by-step guide:

1. Please login as an admin user with admin privileges. Follow the steps described in :ref:`login_with_admin_privileges` for how to do that.

2. Store the obtained admin user token in an environment variable for easy access in subsequent commands:

   .. code-block:: console

      JWT="<value of the obtained access token>"

3. Find out the ID of the runner you want to invalidate. You can find it in the logs of the runner or as a property of any job this runner has completed.

4. Invalidate the runner:

   .. code-block:: console

      curl -X DELETE -H "Authorization: Bearer $JWT" "https://<backend url>/api/admins/invalidate_runner?runner_id=<id of the runner>"

   The runner should now have been deleted from the database, any existing jobs that may have been assigned to that runner will have been re-assigned to a different runner and the token of that runner shouldn't work anymore.
