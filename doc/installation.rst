Installation
============

The following installation guides are for Linux only. Theoretically all the components of this software should be possible to deploy onto other operating systems as well however this is not tested and not supported. You will have to be on your own for that.

.. note::
   The config files shown here are for a setup with local Project-W accounts only. If you want to setup LDAP and/or OIDC, please refer to TODO for more advanced example configs.

.. important::
   If you plan to host the backend public to the internet: Make sure to only serve the backend over https regardless of your installation method! Without ssl encryption sensitive information like passwords, JWT Tokens for the clients and runners or user data will be transmitted in clear text!

.. note::
   Prerequisites: Make sure that your DNS and Firewall settings are correct. In particular, the domain that you want to use has to point to the ip address of your server, and your servers firewall needs to allow incoming tcp traffic on your http port

Docker
------

We provide two docker images, one for the backend that also serves the frontend at the same time, and one for the runner. The best way to use the backend's  In the following we assume that you want to host our backend and client/frontend on the same server, and the runner on a different one. If this assumption doesn't hold for you (e.g. if you want the frontend to be served by a different server than the backends API), then you may have to write your own Dockerfiles and docker-compose.yml or choose a different installation method like NixOS ;).

.. note::
   For both docker images there are multiple docker image tags. The examples below will use the 'latest' tag which will pull the latest stable release (recommended). If you want to pull the development version (latest git commit on main branch), then choose the 'main' tag instead. Alternatively you can also pinpoint the docker image to a specific versions. Go to the Packages section of each GitHub repository to find out which tags are available. To use a tag other than 'latest' add it to the end of the 'image:' lines in the docker-compose.yml files below like this: image: <source>/<name>:<tag>

.. _docker_backend_frontend-label:

Backend & Frontend
``````````````````

Choose between the following instructions depending on your setup. If you are unsure which setup to choose and you want the SSL certificate generation to be as easy as possible then :ref:`reverse_proxy-label` is probably for you.

Standalone
''''''''''

This will setup the backend/frontend without a reverse proxy or any additional components. This guide assumes that you know how to get an SSL certificate for the backend yourself (e.g. by using a self-signed certificate).

1. Install Docker: Refer to your distros package manager / the `Docker documentation <https://docs.docker.com/engine/install/>`_ for this
2. Create initial directory structure and enter project-W directory:

   .. code-block:: console

      mkdir -p project-W/project-W-data/certs && mkdir project-W/project-W-data/postgres && cd project-W

3. To run the backend you need a config.yml file that configures it. You can start off with the following example (don't forget to replace the <placeholders>!) and modify it to your needs if necessary. Put this config file into ./project-W-data. Refer to :ref:`description_backend_config-label` for more information about all the configuration options.

   .. warning::
      Please make sure to store the secrets that are read from an environment variable here in a secret way on your server! Some of these secrets would allow a bad actor to gain full access to Project-W including access to all user data!

   In this setup, the session secret key and the smtp password are being read from the environment variables 'PROJECT_W_JWT_SECRET_KEY' and 'PROJECT_W_SMTP_PASSWORD'. If you want you can also choose to set them here directly in the config, but if you do so please take appropriate measures to keep this config file secret!

   .. code-block:: yaml

      client_url: https://<your domain>/#
      web_server:
      ssl:
        allowed_hosts:
          - localhost
          - <your domain>
        cert_file: '/etc/xdg/project-W/certs/cert.pem'
        key_file: '/etc/xdg/project-W/certs/key.pem'
      postgres_connection_string: !ENV 'postgresql://project_w:${POSTGRES_PASSWORD}@postgres:5432/project_w'
      redis_connection:
        connection_string: 'redis://redis:6379/project-W'
      security:
      local_token:
        session_secret_key: !ENV ${JWT_SECRET_KEY}
      local_account:
        user_provisioning:
          0:
            email: <email of your admin user>
            password: !ENV ${ADMIN_PASSWORD}
            is_admin: true
      smtp_server:
        hostname: <your smtp servers domain>
        port: <smtp port of smtp server>
        secure: <starttls or ssl>
        sender_email: <email address that should send emails to your users>
        username: <probably same as above>
        password: !ENV ${SMTP_PASSWORD}

4. Put your ssl certs into ./project-W-data/certs. Name the cert and key files as specified in the config above (cert.pem and key.pem respectively)
5. Put docker-compose.yml in the current directory. Use the following config and make same adjustments if needed (make sure to replace the <placeholders>!):

   .. code-block:: yaml

      services:
        postgres:
          image: postgres:17
          restart: unless-stopped
          environment:
            - POSTGRES_USER=project_w
            - POSTGRES_PASSWORD=${PROJECT_W_POSTGRES_PASSWORD}
          healthcheck:
            test: ["CMD-SHELL", "pg_isready -U project_w -d project_w"]
            interval: 10s
            retries: 3
            start_period: 30s
            timeout: 10s
          volumes:
            - ./project-W-data/postgres/:/var/lib/postgresql/data
        redis:
          image: redis:8
          restart: unless-stopped
          healthcheck:
            test: ["CMD", "redis-cli", "ping"]
            interval: 10s
            retries: 3
            start_period: 30s
            timeout: 10s
        project-w:
          image: ghcr.io/julianfp/project-w
          restart: unless-stopped
          depends_on:
            postgres:
              condition: service_healthy
            redis:
              condition: service_healthy
          healthcheck:
            test: ["CMD", "curl", "-fk", "https://localhost:5000/api/about"]
            interval: 10s
            retries: 3
            start_period: 30s
            timeout: 10s
          volumes:
            - ./project-W-data/:/etc/xdg/project-W/
          environment:
            - JWT_SECRET_KEY=${PROJECT_W_JWT_SECRET_KEY}
            - SMTP_PASSWORD=${PROJECT_W_SMTP_PASSWORD}
            - POSTGRES_PASSWORD=${PROJECT_W_POSTGRES_PASSWORD}
            - ADMIN_PASSWORD=${PROJECT_W_ADMIN_PASSWORD}
          ports:
            - 443:5000

6. Generate a JWT_SECRET_KEY that will be used to for generating Session Tokens. If you have python installed you can use the following command for this:

   .. code-block:: console

      python -c 'import secrets; print(secrets.token_hex(32))'

7. Run the containers. Replace <JWT Secret Key>, <Your SMTP Password>, <Postgres password> and <project-w admin user password> with the JWT_SECRET_KEY we generated before, the password of the SMTP Server you want to use, some secure password that the admin user should have, and some secure password that you want to use for Postgresql respectively:

   .. code-block:: console

      PROJECT_W_JWT_SECRET_KEY="<JWT Secret Key>" PROJECT_W_SMTP_PASSWORD="<Your SMTP Password>" PROJECT_W_POSTGRES_PASSWORD="<Postgres password>" PROJECT_W_ADMIN_PASSWORD="<project-w admin user password>" docker compose up -d

8. You may want to set up some kind of backup solution. For this you just need to backup the project-W-data directory (which will include the database, your ssl certificate and your config.yml) and maybe your docker-compose.yml if you made changes to it.


.. _reverse_proxy-label:

With Reverse Proxy
''''''''''''''''''

Follow this guide if you want to run this behind a Reverse Proxy which automatically takes care of SSL. This setup will disable https on the backend itself but enable it on the reverse proxy. Please make sure that your users only access the Project-W backend through the reverse proxy in this setup, otherwise their traffic will be unencrypted leaving sensitive data, passwords and token open to attackers!

.. attention::
   This guide will make use of the caddy webserver because of it's automatic handling of https. If you choose to not use caddy as your reverse proxy though then please make sure that your reverse proxy is properly configured to handle the upload of large files. The backend can handle files of many GiB or even larger, limiting this in your reverse proxy will hinder the submission of jobs and present the user with possibly confusing error messages! We will not cover the configuration of the reverse proxy here, but for example if you use nginx you will want to set ``client_max_body_size 0;`` in your config.

1. Install Docker: Refer to your distros package manager / the `Docker documentation <https://docs.docker.com/engine/install/>`_ for this
2. Create initial directory structure and enter project-W directory:

   .. code-block:: console

      mkdir -p project-W/project-W-data && mkdir -p project-W/caddy-data/data && mkdir project-W/caddy-data/config && mkdir project-W/caddy-data/conf && cd project-W

3. Configure Caddy by creating the file called Caddyfile under caddy-data/conf/ with the following content. Please make sure that the DNS record of this domain points to the docker host and that all firewalls and NATs you may have in place are configured to allow traffic on ports 80 AND 443 to the docker host from the internet.

   .. code-block:: Caddyfile
      <the domain under which the backend should be served>

      #configure hsts
      header Strict-Transport-Security "max-age=31536000; includeSubdomains; preload"
      #compression
      encode zstd gzip
      reverse_proxy project-w:5000

4. To run the backend you need a config.yml file that configures it. You can start off with the following example (don't forget to replace the <placeholders>!) and modify it to your needs if necessary. Put this config file into ./project-W-data. Refer to :ref:`description_backend_config-label` for more information about all the configuration options.

   .. warning::
      Please make sure to store the secrets that are read from an environment variable here in a secret way on your server! Some of these secrets would allow a bad actor to gain full access to Project-W including access to all user data!

   In this setup, the session secret key and the smtp password are being read from the environment variables 'PROJECT_W_JWT_SECRET_KEY' and 'PROJECT_W_SMTP_PASSWORD'. If you want you can also choose to set them here directly in the config, but if you do so please take appropriate measures to keep this config file secret!

   .. code-block:: yaml

      client_url: https://<your domain>/#
      web_server:
        allowed_hosts:
          - localhost
          - <your domain>
        reverse_proxy:
          trusted_proxies:
            - "172.16.0.0/12" #private ip range used by docker by default
        no_https: true
      postgres_connection_string: !ENV 'postgresql://project_w:${POSTGRES_PASSWORD}@postgres:5432/project_w'
      redis_connection:
        connection_string: 'redis://redis:6379/project-W'
      security:
      local_token:
        session_secret_key: !ENV ${JWT_SECRET_KEY}
      local_account:
        user_provisioning:
          0:
            email: <email of your admin user>
            password: !ENV ${ADMIN_PASSWORD}
            is_admin: true
      smtp_server:
        hostname: <your smtp servers domain>
        port: <smtp port of smtp server>
        secure: <starttls or ssl>
        sender_email: <email address that should send emails to your users>
        username: <probably same as above>
        password: !ENV ${SMTP_PASSWORD}

5. Put docker-compose.yml in the current directory. Use the following config and make same adjustments if needed (make sure to replace the <placeholders>!):

   .. code-block:: yaml

      services:
        postgres:
          image: postgres:17
          restart: unless-stopped
          environment:
            - POSTGRES_USER=project_w
            - POSTGRES_PASSWORD=${PROJECT_W_POSTGRES_PASSWORD}
          healthcheck:
            test: ["CMD-SHELL", "pg_isready -U project_w -d project_w"]
            interval: 10s
            retries: 3
            start_period: 30s
            timeout: 10s
          volumes:
            - ./project-W-data/postgres/:/var/lib/postgresql/data
        redis:
          image: redis:8
          restart: unless-stopped
          healthcheck:
            test: ["CMD", "redis-cli", "ping"]
            interval: 10s
            retries: 3
            start_period: 30s
            timeout: 10s
        project-w:
          image: ghcr.io/julianfp/project-w
          restart: unless-stopped
          depends_on:
            postgres:
              condition: service_healthy
            redis:
              condition: service_healthy
          healthcheck:
            test: ["CMD", "curl", "-fk", "http://localhost:5000/api/about"]
            interval: 10s
            retries: 3
            start_period: 30s
            timeout: 10s
          volumes:
            - ./project-W-data/:/etc/xdg/project-W/
          environment:
            - JWT_SECRET_KEY=${PROJECT_W_JWT_SECRET_KEY}
            - SMTP_PASSWORD=${PROJECT_W_SMTP_PASSWORD}
            - POSTGRES_PASSWORD=${PROJECT_W_POSTGRES_PASSWORD}
            - ADMIN_PASSWORD=${PROJECT_W_ADMIN_PASSWORD}
        caddy:
          image: caddy:2
          restart: unless-stopped
          cap_add:
            - NET_ADMIN
          depends_on:
            project-w:
              condition: service_healthy
          volumes:
            - ./caddy-data/data:/data
            - ./caddy-data/config:/config
            - ./caddy-data/conf:/etc/caddy
          ports:
            - 80:80
            - 443:443
            - 443:443/udp

6. Generate a JWT_SECRET_KEY that will be used to for generating Session Tokens. If you have python installed you can use the following command for this:

   .. code-block:: console

      python -c 'import secrets; print(secrets.token_hex(32))'

7. Run the containers. Replace <JWT Secret Key>, <Your SMTP Password>, <Postgres password> and <project-w admin user password> with the JWT_SECRET_KEY we generated before, the password of the SMTP Server you want to use, some secure password that the admin user should have, and some secure password that you want to use for Postgresql respectively:

   .. code-block:: console

      PROJECT_W_JWT_SECRET_KEY="<JWT Secret Key>" PROJECT_W_SMTP_PASSWORD="<Your SMTP Password>" PROJECT_W_POSTGRES_PASSWORD="<Postgres password>" PROJECT_W_ADMIN_PASSWORD="<project-w admin user password>" docker compose up -d

8. You may want to set up some kind of backup solution. For this you just need to backup the project-W-data directory (which will include the database and your config.yml), the caddy-data directory (which will include your ssl certs, ocsp staples and so on) and maybe your docker-compose.yml if you made changes to it.

Runner
``````

The runner runs the whisper model and thus benefits greatly from running on a GPU, which we heavily recommend. This GPU should have at least 10GB of VRAM available, ideally a bit more. If you don't have a powerful enough GPU available though you can choose to also run it on CPU. Choose between the following instructions depending on your choice. Currently we have only instructions for NVIDIA GPUs using CUDA but it should also be possible to run this on an AMD GPU using ROCM (for this you are on your own though).

NVIDIA GPU
''''''''''

1. If you don't already have one then create an hugging face account, then using that account accept the conditions for the `pyannote/segmentation-3.0 <https://huggingface.co/pyannote/segmentation-3.0>`_ and `pyannote/speaker-diarization-3.1 <https://huggingface.co/pyannote/speaker-diarization-3.1>`_ models. Create a token with access permissions to these repositories (e.g. by just granting the 'Read access to contents of all public gated repos you can access' permission).

2. Install Docker: Refer to your distros package manager / the `Docker documentation <https://docs.docker.com/engine/install/>`_ for this

3. Install the NVIDIA container toolkit. Refer to the `NVIDIA toolkit documentation <https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html>`_ for this. Don't forget to restart your docker daemon afterwards.

4. Create initial directory structure and enter project-w directory:

   .. code-block:: console

      mkdir -p project-W/runner-config && mkdir project-W/runner-models && cd project-W

5. Like for the backend you also need a config.yml file for the runner. Prepare this file before following the installation steps below. You can use the following example as a base (don't forget to replace the <placeholder>!) and modify it to your needs if necessary. Put this file into ./runner-config. Refer to :ref:`description_runner_config-label` for more information about all the configuration options of the runner.

   .. warning::
      Please make sure to store the secrets that are read from an environment variable here in a secret way on your server! Some of these secrets would allow a bad actor to gain full access to Project-W including access to all user data!

   In this setup, the auth token and the hugging face token are read from the environment variable 'PROJECT_W_AUTH_TOKEN' and 'PROJECT_W_HF_TOKEN' respectively. If you want you can also choose to set it directly in the config, but if you do so please take appropriate measures to keep this config file secret!

   .. code-block:: yaml

      runner_attributes:
        name: "<name of your runner how it should be shown to your users>"
      backend_settings:
        url: https://<domain of your Project-W backend>
        auth_token: !ENV ${AUTH_TOKEN}
      whisper_settings:
        hf_token: !ENV ${HF_TOKEN}
        model_cache_dir: /models


6. Put docker-compose.yml in the current directory. Use the following config and make adjustments if needed

   .. code-block:: yaml

      services:
        runner:
          image: ghcr.io/julianfp/project-w_runner
          restart: unless-stopped
          volumes:
            - ./runner-config:/etc/xdg/project-W-runner/
            - ./runner-models:/models
          environment:
            - AUTH_TOKEN=${PROJECT_W_AUTH_TOKEN}
            - HF_TOKEN=${PROJECT_W_HF_TOKEN}
          deploy:
            resources:
              reservations:
                devices:
                  - driver: nvidia
                    count: 1
                    capabilities: [gpu]

   .. note::
      Alternatively if you have a system with multiple GPUs and you want to have more control over which GPU gets allocated to the Runner, you can replace 'count: 1' above with 'count: all' and then select the GPU in the config.yml using the 'whisper_settings.torch_device' option. See :ref:`description_runner_config-label`.

7. Create a new Runner and obtain its runner token. Refer to :doc:`connect_runner_backend` for how to do that.

8. Run the container. Replace <Runner Token> with the runner token you obtained from the backend in the previous step:

   .. code-block:: console

      PROJECT_W_AUTH_TOKEN="<obtained runner token>" PROJECT_W_HF_TOKEN="<your huggingface token>" docker compose up -d

9. You may want to back up the runners config file (in ./runner-config) and the docker-compose.yml file if you made any changes to them. The ./runner-models directory contains all the whisper models that the runner will fetch automatically. You don't need to backup this directory but you can keep this directory around, copy it to other machines and share it between runners so that the runner doesn't need to spend time fetching these models anymore and so that if you have multiple runners on the same machine the models don't take up storage space multiple times!

CPU
'''

1. If you don't already have one then create an hugging face account, then using that account accept the conditions for the `pyannote/segmentation-3.0 <https://huggingface.co/pyannote/segmentation-3.0>`_ and `pyannote/speaker-diarization-3.1 <https://huggingface.co/pyannote/speaker-diarization-3.1>`_ models. Create a token with access permissions to these repositories (e.g. by just granting the 'Read access to contents of all public gated repos you can access' permission).

2. Install Docker: Refer to your distros package manager / the `Docker documentation <https://docs.docker.com/engine/install/>`_ for this

3. Create initial directory structure and enter project-w directory:

   .. code-block:: console

      mkdir -p project-W/runner-config && mkdir project-W/runner-models && cd project-W

4. Like for the backend you also need a config.yml file for the runner. Prepare this file before following the installation steps below. You can use the following example as a base (don't forget to replace the <placeholder>!) and modify it to your needs if necessary. Put this file into ./runner-config. Refer to :ref:`description_runner_config-label` for more information about all the configuration options of the runner.

   .. warning::
      Please make sure to store the secrets that are read from an environment variable here in a secret way on your server! Some of these secrets would allow a bad actor to gain full access to Project-W including access to all user data!

   In this setup, the auth token and the hugging face token are read from the environment variable 'PROJECT_W_AUTH_TOKEN' and 'PROJECT_W_HF_TOKEN' respectively. If you want you can also choose to set it directly in the config, but if you do so please take appropriate measures to keep this config file secret!

   .. code-block:: yaml

      runner_attributes:
        name: "<name of your runner how it should be shown to your users>"
      backend_settings:
        url: https://<domain of your Project-W backend>
        auth_token: !ENV ${AUTH_TOKEN}
      whisper_settings:
        hf_token: !ENV ${HF_TOKEN}
        model_cache_dir: /models
        torch_device: cpu
        compute_type: int8
        batch_size: 4


5. Put docker-compose.yml in the current directory. Use the following config and make adjustments if needed

   .. code-block:: yaml

      services:
        runner:
          image: ghcr.io/julianfp/project-w_runner
          restart: unless-stopped
          volumes:
            - ./runner-config:/etc/xdg/project-W-runner/
            - ./runner-models:/models
          environment:
            - AUTH_TOKEN=${PROJECT_W_AUTH_TOKEN}
            - HF_TOKEN=${PROJECT_W_HF_TOKEN}

6. Create a new Runner and obtain its runner token. Refer to :doc:`connect_runner_backend` for how to do that.

7. Run the container. Replace <Runner Token> with the runner token you obtained from the backend in the previous step:

   .. code-block:: console

      PROJECT_W_AUTH_TOKEN="<obtained runner token>" PROJECT_W_HF_TOKEN="<your huggingface token>" docker compose up -d

8. You may want to back up the runners config file (in ./runner-config) and the docker-compose.yml file if you made any changes to them. The ./runner-models directory contains all the whisper models that the runner will fetch automatically. You don't need to backup this directory but you can keep this directory around, copy it to other machines and share it between runners so that the runner doesn't need to spend time fetching these models anymore and so that if you have multiple runners on the same machine the models don't take up storage space multiple times!

NixOS
-----

We provide NixOS flakes for the backend, frontend and runner. Each of them include a NixOS module to setup the service, a nix-shell for development purposes as well as a package and overlay for running the service manually if desired. We will focus on the NixOS module here.

Backend
```````

First you need to import our flake into your flake containing the NixOS config of your machine. For this add the following to your 'inputs' section of your flake.nix:

    .. code-block:: Nix

        inputs = {
          ...
          project-W = {
            url = "github:JulianFP/project-W";
            inputs.nixpkgs.follows = "nixpkgs";
          };
        };

Next you need to pass your inputs as an argument to your outputs, where you then can import the module and apply the overlay:

    .. code-block:: Nix

        nixosConfiguration.<your machines hostname> = nixpkgs.lib.nixosSystem {
          ...
          pkgs = import nixpkgs {
            ...
            overlays = [
               inputs.project-W.overlays.default
            ];
          };
          modules = [
            inputs.project-W.nixosModules.default
            ...
          ];
        };

Now you can start using the module. For a full list and description of options go to nix/module.nix in the project-W repository. Also the `settings` attribute set is basically just a copy of the options of the config file (however with different default values), so you can also refer to :ref:`description_backend_config-label` for this part. However the following config should get you started as well:

.. warning::
    The options 'settings.loginSecurity.sessionSecretKey' and 'settings.smtpServer.password' are available, but they are not very secure since it's contents will be public in the nix store! We strongly recommend to use the envFile option to add the secrets to your config. If you want your secrets to be part of your NixOS config, then please use sops-nix or agenix for that.

.. code-block:: Nix

   services.project-W-backend = {
     enable = true;
     hostName = "<DOMAIN>";
     settings = {
       clientURL = "https://<DOMAIN where frontend is hosted>/#";
       smtpServer = {
         domain = "<smtp servers domain>";
         port = <port of smtp server>;
         secure = "<ssl or starttls>";
         senderEmail = "<email registered at smtp server>";
         username = config.services.project-W-backend.senderEmail; #probably, if not the same then set something different here
       };
     };
     envFile = "<path to env file>";
   };
   services.nginx.virtualHosts.${config.services.project-W-backend.hostName} = {
     forceSSL = true;
     http2 = true;
     enableACME= true;
   };
   security.acme = {
     acceptTerms = true;
     certs = {
       ${config.services.project-W-backend.hostName}.email = "<your email address for let's encrypt>";
     };
   };

This setup already enables https and automatic ssl certificate renewal over let's encrypt for you. If you want to run this behind a reverse proxy, then just leave the nginx and acme part away.

.. attention::
   If you use a Reverse Proxy: Make sure that your reverse proxy is properly configured to handle the upload of large files. The backend can handle files up to a size of 1GB, setting this to anything less in your reverse proxy will hinder the submission of jobs and present the user with possibly confusing error messages! We will not cover the configuration of the reverse proxy here, but for example if you use nginx you will want to set ``client_max_body_size 1g;`` in your config.

The envFile should contain the following. Please make sure to keep this secret!!!:

.. code-block:: console

   JWT_SECRET_KEY="<your jwt secret key>"
   SMTP_PASSWORD="<password of user at your smtp server>"

The JWT_SECRET_KEY can be generated with the following command:

.. code-block:: console

   nix run nixpkgs#python3 -- -c 'import secrets; print(secrets.token_hex())'

Rebuild your NixOS config and you are done! The backend now running under the systemd service 'project-W-backend.service' and is being served by nginx (in case you need to check the logs).

If you want to do backups, you just need to backup the directory that is set with 'settings.databasePath' (per default: /var/lib/project-W-backend/database) as well as the directory where acme stores the ssl certificates (per default: /var/lib/acme/<DOMAIN>). Of course you also need to backup your NixOS config, but you probably have that in a git repo anyway ;)

Frontend
````````

First you need to import our flake into your flake containing the NixOS config of your machine. For this add the following to your 'inputs' section of your flake.nix:

.. code-block:: Nix

   inputs = {
     ...
     project-W-frontend = {
       url = "github:JulianFP/project-W-frontend";
       inputs.nixpkgs.follows = "nixpkgs";
     };
   };

Next you need to pass your inputs as an argument to your outputs, where you then can import the module (for the frontend no overlay is required):

.. code-block:: Nix

   nixosConfiguration.<your machines hostname> = nixpkgs.lib.nixosSystem {
     ...
     modules = [
       inputs.project-W-frontend.nixosModules.default
       ...
     ];
   };

Now you can start using the module. For a full list and description of options go to nix/module.nix in the project-W-frontend repository. However the following config should get you started as well:

.. code-block:: Nix

   services.project-W-frontend = {
     enable = true;
     hostName = "<DOMAIN>";
     backendBaseURL = "https://<Backends DOMAIN>"; #leave to default if both domains are the same
   };
   services.nginx.virtualHosts.${config.services.project-W-frontend.hostName} = {
     forceSSL = true;
     http2 = true;
     enableACME= true;
   };
   security.acme = {
     acceptTerms = true;
     certs = {
       ${config.services.project-W-frontend.hostName}.email = "<your email address for let's encrypt>";
     };
   };

This setup already enables https and automatic ssl certificate renewal over let's encrypt for you. If you want to run this behind a reverse proxy, then just leave the nginx and acme part away.

Rebuild your NixOS config and you are done! The frontend is now being served by nginx (in case you need to check the logs).

Runner
``````

First you need to import our flake into your flake containing the NixOS config of your machine. For this add the following to your 'inputs' section of your flake.nix:

.. code-block:: Nix

   inputs = {
     ...
     project-W-runner = {
       url = "github:JulianFP/project-W-runner";
       inputs.nixpkgs.follows = "nixpkgs";
     };
   };

Next you need to pass your inputs as an argument to your outputs, where you then can import the module (for the runner no overlay is required either):

.. code-block:: Nix

   nixosConfiguration.<your machines hostname> = nixpkgs.lib.nixosSystem {
     ...
     modules = [
       inputs.project-W-runner.nixosModules.default
       ...
     ];
   };

Now you can start using the module. For a full list and description of options go to nix/module.nix in the project-W-runner repository. Also the `settings` attribute set is basically just a copy of the options of the runner config file (however with different default values), so you can also refer to :ref:`description_runner_config-label` for this part. However the following config should get you started as well:

.. warning::
    The option 'settings.runnerToken' is available, but it is not very secure since it's content will be public in the nix store! We strongly recommend to use the envFile option to add the secrets to your config. If you want your secrets to be part of your NixOS config, then please use sops-nix or agenix for that.

.. code-block:: Nix

   services.project-W-runner = {
     enable = true;
     settings = {
       backendURL = "<URL of your backend>";
       #torchDevice = "cuda:0"; #only enable this if you want to tell pytorch explicitly to use the first cuda device of the system
     };
     envFile = "<path to env file>";
   };

The envFile should contain the following. Please make sure to keep this secret!!!:

.. code-block:: console

   RUNNER_TOKEN="<your runners token>"

Rebuild your NixOS config and you are done! The runner is running under the systemd service 'project-W-runner.service'.

By default, whisper models will be cached in the `/var/cache/project-W-runner_whisperCache` directory. Go there if you want to replace them.

.. note::
   We didn't test if the NixOS module would work with CUDA since we didn't have access to a NixOS machine with NVIDIA GPUs. If additional configuration in the module should be necessary: Contributions welcome!

For CUDA support please add the cuda toolkit you want to use to `environment.systemPackages` in your NixOS config.

.. _manual_installation-label:

Manual installation
-------------------

You can also run Project-W barebones. This can be a bit more difficult and the following steps will not be as detailed as the ones with Docker or NixOS. You will have to do stuff like configuring python virtual environments, setting up webservers or compiling the frontend yourself.

Backend & Frontend
``````````````````

The frontend is written in Svelte and needs to be compiled into native Javascript. To do this you will need some build dependencies, however you can remove them after step 4. If you want you can even build it on a different machine and then just move the build directory to the server between step 4 and 5.

1. Install nodejs

2. Clone the frontend repository and enter it:

   .. code-block:: console

      git clone https://github.com/JulianFP/project-W-frontend.git & cd project-W-frontend

3. Install pnpm:

   .. code-block:: console

      npm install -g pnpm

4. Install all build dependencies:

   .. code-block:: console

      pnpm install

4. Build the frontend:

   .. code-block:: console

      pnpm build

You can find the result in the ./build directory. Now we will now setup the backend which will serve the static files inside this build directory together with the API. This way the frontend and the API are served from the same origin.

5. Install Python (3.11 or newer, I have tested 3.11 to 3.13) and pip

6. Clone this repository and enter it:

   .. code-block:: console

      git clone https://github.com/JulianFP/project-W.git & cd project-W

7. Install the package with pip:

   .. code-block:: console

      python -m pip install .

8. Spin up a Postgresql and Redis server (outside of the scope of this tutorial) and put the config.yml file of the backend either into /etc/xdg/project-W/ or ~/.config/project-W/. Alternatively you can also set a custom path to the config file using the `--custom_config_path` CLI option in the command below.

9. Run the backend server:

   .. code-block:: console

      project_W --root_static_files <path to the build directory of the frontend>


Runner
``````

1. Install Python (3.11 or 3.12, I have mostly tested 3.12), pip, and ffmpeg.

2. Clone this repository and enter it:

   .. code-block:: bash

      git clone https://github.com/JulianFP/project-W-runner.git & cd project-W-runner

3. Install the package including the whisperx dependencies with pip:

   .. code-block:: bash

      python -m pip install .[not_dummy]

4. Put the config.yml file of the runner either into /etc/xdg/project-W-runner/ or ~/.config/project-W-runner/. Alternatively you can also set a custom path to the config file using the `--custom_config_path` CLI option in the command below.

5. Start up the runner:

   .. code-block:: bash

      project_W_runner

6. You may want to make sure that the runner will always restart itself even if it crashes. Currently this might happen in rare cases, so maybe write a script or a systemd service that will always automatically restart the runner in case of a crash.
