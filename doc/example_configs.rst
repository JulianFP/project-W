More example configs
====================

This page contains a collection of example snippets from config files for more advanced usage than what was shown in :doc:`installation`. These are just meant as examples to teach you the available config options, feel free to adjust and mix and match these examples.

.. note::
   The shown configs are not necessarily complete config files. Please refer to :doc:`installation` for a complete config file to get you started, and then use the following snippets to extend/modify this config file.

Add an imprint
--------------

An imprint is often required for legal reasons and contains information about who is hosting your instance. There are two ways to add an imprint to your Project-W instance: Either you add an URL pointing to an imprint page hosted somewhere else, or you add custom imprint html for a dedicated imprint page on the Project-W frontend itself. Please note that in both versions the ``name`` field is always required since it is used as a link name in the API specification. Put your or your organizations name into this field. The ``email`` field adds a contact email address to the API specification and can be used in both imprint configurations but is optional.

Dedicated imprint page
``````````````````````

Reference this example config to show an imprint on the Project-W frontend itself:

.. code-block:: yaml

   imprint:
     name: Alice
     email: alice@example.org
     additional_imprint_html: |
       <div>
         <dt><strong>Phone number:</strong></dt>
         <dd><a href="tel:012345678">012345678</a></dd>
       </div>
       <div>
         <dt><strong>Address:</strong></dt>
         <dd>alice square 42, 424242 alicetown, alice's kingdom</dd>
       </div>
       <div>
         <dt><strong>Website:</strong></dt>
         <dd><a href="https://alice.example.org" target="_blank" rel="noopener noreferrer">alice.example.org</a></dd>
       </div>

External imprint page
`````````````````````

Reference this example config to link to an imprint page hosted somewhere else:

.. code-block:: yaml

   imprint:
     name: Alice
     email: alice@example.org
     url: https://example.org/imprint

Add Terms of Services
---------------------

A User Agreement or a Data Privacy Agreement can often be a legal requirement for hosting an instance like this. While Project-W doesn't offer any legal insurances it does offer features to the administrator so that they can figure out the legal requirements themselves and hopefully implement them.

The following config is for demonstration purposes only:

.. code-block:: yaml

   terms_of_services:
     0:
       name: User Agreement
       version: 1
       tos_html: |
         <p>The user agrees to donate their kidney to the developer of Project-W</p>
     1:
       name: Data Privacy Agreement
       version: 1
       tos_html: |
         <p>You can find the full data privacy agreement <a href="https://tos.example.org" target="_blank" rel="noopener noreferrer">here</a></p>

This config adds two separate terms of services. The user has to explicitly accept both of them before being able to use Project-W (i.e. upload any jobs etc.). While the official frontend leaves plenty of space for longer terms of services than shown here, for many pages worth of legal text consider using a link instead as shown in the Data Privacy Agreement above.

The version field can't be omitted and is important when updating the terms of services: If you increase the version integer all users will have to re-read and re-accept this term of service. Always increase the version if you make significant changes to the terms of services.

Never change the keys of these attributes sets (here 0 and 1) since they are being used to identify each term of service. If you want to remove a term of service then never reuse that same key for a different term of service in the future as the users will still have accepted the term of service with that key even if it has been removed from the config. The name and tos_html of the term of service however can be changed as much as you want (just consider to increase the version field alongside it).

Basic OIDC login with GitLab
----------------------------

With this config any user of gitlab.com or some other GitLab instance of your choice will be able to use Project-W, while none of them will have admin privileges. I choose GitLab as the first example because it is probably one of the easiest OIDC providers to setup with Project-W (at least of the public ones), making it easily adaptable to other OIDC providers as well.

1. Login on your GitLab instance, click on your account profile icon and click on `Preferences`. Navigate to `Applications` and click `Add new application`

2. Set a name, set `https://<backend domain>/api/oidc/auth/gitlab` as a redirect URI, and select the `openid` and `email` scopes.

3. Click `Save application` and then from the overview that appears copy the `Application ID` and the `Secret` into your clipboard

4. Add the following config snippet to your backend's config file and fill in the copied credentials (and change the base_url to your GitLab's url if you want to use a different GitLab instance):

   .. code-block:: yaml

      security:
        oidc_providers:
          GitLab:
            icon_url: "https://gitlab.com/assets/logo-911de323fa0def29aaf817fca33916653fc92f3ff31647ac41d2c39bbe243edb.svg"
            base_url: "https://gitlab.com"
            client_id: "<the Application ID you copied>"
            client_secret: "<the Secret you copied>"

   .. note::
      If you change the name of the provider in the config then you need to change it in the redirect URI as well, so changing the provider name will break the OIDC setup! The providers name in the redirect URI is the same is in the config, but in all lower case letters and with spaces striped from beginning and end. If you want to use spaces in the middle of the name (or any other special characters) then you need to escape them in the redirect URI.

Basic OIDC login with Google
----------------------------

With this config any Google user will be able to use Project-W, while none of them will have admin privileges. This will be similar to the GitLab guide with some minor Google-specific fixes.

1. Go to the `Google Cloud console <https://console.cloud.google.com>`_, login with a Google account of your choice and navigate to `APIs and services -> Credentials -> Create credentials -> OAuth client ID`

2. As an application type choose `Web application` and enter a name. Add `https://<backend domain>` as an URI to `Authorised JavaScript origins` and `https://<backend domain>/api/oidc/auth/google` as an URI to `Authorised redirect URIs`

3. Click `Create` and then from the popup that appears copy the `Client ID` and `Client secret` into your clipboard

4. Add the following config snippet to your backend's config file and fill in the copied credentials:

   .. code-block:: yaml

      security:
        oidc_providers:
          Google:
            icon_url: "https://fonts.gstatic.com/s/i/productlogos/googleg/v6/128px.svg"
            base_url: "https://accounts.google.com"
            client_id: "<the Client ID you copied>"
            client_secret: "<the Client secret you copied>"
            additional_authorize_params: #Google specific
              access_type: "offline"
              prompt: "consent"

   .. note::
      Even with the provided additional_authorize_params, Google seems to limit the amount of valid request tokens that can exist at the same time and thus automatically invalidate refresh tokens. This might compromise the validity of long lived API tokens issued by Google accounts!

OIDC login restricted to a user group
-------------------------------------

If you/your organization are hosting your own identity provider that you want to use for Project-W, but you don't want to give all registered users at that provider access to the service, then this example config might be for you. Project-W allows you to restrict access to certain user roles which are read from the claims of the id_token.

1. Configure your IdP with a custom claim map. The name and value of that claim are up to you, just make sure that only the users who are supposed to have access to Project-W have that claim with that specific value. I use `Kanidm <https://kanidm.com>`_ as my IdP, if you do too then `here is the documentation for how to do this <https://kanidm.github.io/kanidm/master/integrations/oauth2/custom_claims.html>`_.

2. If you want then you can do the same for a different group of users that should have admin privileges as well. Please be careful though as having admin privileges gives a user full access over the data of all users on the instance! Refer to :ref:`login_with_admin_privileges` for more information on that.

3. Here is an example config file for Kanidm that uses custom claims to restrict user access and give some users admin privileges. The admin_role section can be omitted if no user should have admin privileges, and the ca_pem_file_path option can of course also be omitted if you didn't self-sign your certificate:

   .. code-block:: yaml

      oidc_providers:
        Kanidm:
          ca_pem_file_path: <path to the certificate of the Kanidm instance since I self-signed it>
          icon_url: "https://kanidm.com/images/logo.svg"
          base_url: "https://localhost:8443/oauth2/openid/project-w"
          client_id: project-w
          client_secret: <redacted>
          user_role:
            field_name: "role"
            name: "user"
          admin_role:
            field_name: "role"
            name: "admin"

LDAP login
----------

If you want to use LDAP instead of OIDC for logging in your users this guide is for you.

1. Create an LDAP service account that the backend can bind to. It will be used to query the users. This account should have access to all users that should be able to login with Project-W including their usernames, email addresses as well as all other attributes you may want to use in your filter expression. It DOESN'T need to have access to user passwords (since the backend will perform a bind with a queried LDAP user to check if a provided password was correct)

2. For querying the users the backend also needs a base dn (which should be a dn under which all users that should have access are located) as well as a filter expression that exactly returns one user, namely the one with the provided username. What exactly this username is is up to you (it can be the email address, but doesn't have to be). The placeholder for this username value is ``%s``, you need to include this placeholder in your filter expression. If you only want to match users that are part of a specific group or similar you can also do that in the filter expression. Usually you should at list filter for the entity class in addition to the username (e.g. ``class=account``).

3. You need to provide the backend with an attribute name that every user has that contains the user's email address. The reason for this is that different LDAP servers call this field differently: Sometimes it's called `mail`, sometimes `email` or sometimes something entirely different. Every user needs to have an email address attached to it that is stored in this attribute name. This is a hard requirement since the backend sends emails to the user on several occasions (e.g. job completion notifications).

4. If you want you can craft a different filter expression, base dn and mail attribute name for a different user group that should have admin privileges as well. Please be careful though as having admin privileges gives a user full access over the data of all users on the instance! Refer to :ref:`login_with_admin_privileges` for more information on that.

5. I use `Kanidm <https://kanidm.com>`_ as my IdP, if you do too then `here is it's documentation for setting up the LDAP interface <https://kanidm.github.io/kanidm/master/integrations/ldap.html>`_. If your IdP is ready to go then you just need to add a config similar to the following to the backend. The admin_query section can be omitted if no user should have admin privileges, and the ca_pem_file_path option can of course also be omitted if you didn't self-sign your certificate:

   .. code-block:: yaml

      ldap_providers:
        Kanidm LDAP:
          ca_pem_file_path: <path to the certificate of the Kanidm instance since I self-signed it>
          icon_url: "https://kanidm.com/images/logo.svg"
          server_address: "ldaps://127.0.0.1:3636"
          service_account_auth:
            user: "dn=token"
            password: <redacted>
          username_attributes:
            - "name"
            - "mail"
          uid_attribute: "uuid"
          mail_attribute: "mail"
          user_query:
            base_dn: "dc=localhost"
            filter: "&(class=account)(memberof=spn=project-W-users@localhost)"
          admin_query:
            base_dn: "dc=localhost"
            filter: "&(class=account)(memberof=spn=project-W-admins@localhost)"

Automatic user and job cleanups
-------------------------------

The backend always deletes the submitted audio files (which is both the most sensitive and storage consuming data) as soon as possible, i.e. immediately after the job has finished, failed or was aborted. However by default, all other data (like transcripts, job information and settings, user emails and account information, ...) will be kept indefinitely.

For various reasons it might be desirable to change this behavior. For this Project-W provides automatic cleanup functionality for both jobs and users. This feature might proof especially useful to comply with possible regulatory requirements which dictate that user data can only be kept for a certain amount of time.

   .. note::
      This feature relies on the periodic tasks being executed at least daily. Please use the provided project-w_cron docker container or setup a cronjob or systemd timer for this if you haven't already. If the periodic tasks are misconfigured this feature will not work correctly or at all!

Here is an example config that deletes jobs 7 days after they have finished and users 1 year after their last login:

   .. code-block:: yaml

      cleanup:
        finished_job_retention_in_days: 7
        user_retention_in_days: 365

Of course you can also decide to activate only one of user or job deletion without the other. By default, both are deactivated.

If a job gets deleted this means that all data attached to that job, most notably the transcript, will also be deleted. Since the transcript is almost as sensitive as the audio files themselves you might want to setup your Project-W instance to store jobs only very briefly to minimize the amount of sensitive data stored on the backend at every given time (e.g. to 7 days like in this example). If job deletion is active the users will be informed about that on the job submission page so that they can make sure to download the transcript of a finished job before it gets deleted.

If a user gets deleted this means that all data attached to that user, most notably all of their jobs, transcripts and their account information and email address, will also be deleted. An email will be sent to affected users both 30 days and 7 days before their account will be deleted which gives them a chance to login to Project-W again and thus save their account from deletion.

Configure logging
-----------------

You may want to configure how logs are handled, e.g.:

- Enable file logging
- Change the general format of the logs
- Change how dates are formatted in the logs
- Enable json logs for machine readability (e.g. for logging aggregation software like Grafana Loki)
- Set the log level

We provide a logging stack that can do all of this. It is also shared across the backend and the runner, meaning the following example configuration is valid for both the backend's and the runner's config file.

   .. code-block:: yaml

      logging:
        console:
          fmt: "<%(levelname)s> [%(asctime)s | %(name)s] %(message)s"
          datefmt: "%m/%d/%Y %I:%M%p"
          level: WARNING
        file:
          path: ./file.log
          json_fmt: true
          level: DEBUG

This config snippet enables logging into the specified file.log file in json format while setting the log level to DEBUG for this. Please note that the DEBUG level will generate a lot of logs that will include sensitive data and that it may reduce application performance. At the same time, the snippet also changes the format of the console logging, and sets the log level for the console to WARNING. As you can see, you can change console logging settings and file logging settings independently from each other.
