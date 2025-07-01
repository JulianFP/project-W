More example configs
====================

This page contains a collection of example snippets from config files for more advanced usage than what was shown in :doc:`installation`. These are just meant as examples to teach you the available config options, feel free to adjust and mix and match these examples.

.. note::
   The shown configs are not necessarily complete config files. Please refer to :doc:`installation` for a complete config file to get you started, and then use the following snippets to extend/modify this config file.

Add an imprint
--------------

An imprint is often required for legal reasons and contains information about who is hosting this instance. The name and email fields are required, but then you can add arbitrary html to the imprint a add any information you want.

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
         <dd><a href="alice.example.org" target="_blank" rel="noopener noreferrer">alice.example.org</a></dd>
       </div>

Basic OIDC login with Google
----------------------------

With this config any Google user will be able to use Project-W, while none of them will have admin privileges. This guide should easily be adaptable to other OIDC providers as well.

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

   .. note::
      If you change the name of the provider in the config then you need to change it in the redirect URI as well, so changing the provider name will break the OIDC setup! The providers name in the redirect URI is the same is in the config, but in all lower case letters and with spaces striped from beginning and end. If you want to use spaces in the middle of the name (or any other special characters) then you need to escape them in the redirect URI.

OIDC login restricted to a user group
-------------------------------------

If you/your organization are hosting your own identity provider that you want to use for Project-W, but you don't want to give all registered users at that provider access to the service, then this example config might be for you. Project-W allows you to restrict access to certain user roles which are read from the claims of the id_token.

1. Configure your IdP with a custom claim map. The name and value of that claim are up to you, just make sure that only the users who are supposed to have access to Project-W have that claim with that specific value. I use `Kanidm <https://kanidm.com>`_ as my IdP, if you do too then you can find the documentation for how to do this `here <https://kanidm.github.io/kanidm/master/integrations/oauth2/custom_claims.html>`_.

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

5. I use `Kanidm <https://kanidm.com>`_ as my IdP, if you do too then you can find the documentation for how to set up it's LDAP interface `here <https://kanidm.github.io/kanidm/master/integrations/ldap.html>`_. If your IdP is ready to go then you just need to add a config similar to the following to the backend. The admin_query section can be omitted if no user should have admin privileges, and the ca_pem_file_path option can of course also be omitted if you didn't self-sign your certificate:

   .. code-block:: yaml

      ldap_providers:
        Kanidm LDAP:
          ca_pem_file_path: <path to the certificate of the Kanidm instance since I self-signed it>
          icon_url: "https://kanidm.com/images/logo.svg"
          server_address: "ldaps://127.0.0.1:3636"
          service_account_auth:
            user: "dn=token"
            password: <redacted>
          user_query:
            base_dn: "dc=localhost"
            filter: "(&(class=account)(memberof=spn=project-W-users@localhost)(name=%s))"
            uid_attribute_name: "uuid"
            mail_attribute_name: "mail"
          admin_query:
            base_dn: "dc=localhost"
            filter: "(&(class=account)(memberof=spn=project-W-admins@localhost)(name=%s))"
            uid_attribute_name: "uuid"
            mail_attribute_name: "mail"
