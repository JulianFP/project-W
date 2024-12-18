Installation
============

The following installation guides are for Linux only. Theoretically all the components of this software should be possible to deploy onto other operating systems as well however this is not tested and not supported. You will have to be on your own for that.

.. important::
   If you plan to host the backend public to the internet: Make sure to only serve the backend over https regardless of your installation method! Without ssl encryption sensitive information like passwords, JWT Tokens for the clients and runners or user data will be transmitted in clear text!

.. note::
   Prerequisites: Make sure that your DNS and Firewall settings are correct. In particular, the domain that you want to use has to point to the ip address of your server, and your servers firewall needs to allow incoming tcp traffic on ports 80 and 443 (only on port 80 if you go with the reverse proxy setup)

Docker
------

We provide a docker image for each of the components of this software (client, backend, runner). The best way to use them is with Docker Compose. In the following we assume that you want to host our backend and client/frontend on the same server, and the runner on a different one. If this assumption doesn't hold for you (e.g. if you want the frontend to be served by a different server than the backends API), then you may have to write your own Dockerfiles and docker-compose.yml or choose a different installation method like NixOS ;).

.. note::
   For each of the three components there are multiple docker image tags. The examples below will use the 'latest' tag which will pull the latest stable release (recommended). If you want to pull the development version (latest git commit on main branch), then choose the 'main' tag instead. Alternatively you can also pinpoint the docker image to a specific versions. Go to the Packages section of each GitHub repository to find out which tags are available. To use a tag other than 'latest' add it to the end of the 'image:' lines in the docker-compose.yml files below like this: image: <source>/<name>:<tag>

.. _docker_backend_frontend-label:

Backend & Frontend
``````````````````

To run the backend you need a config.yml file that configures it. Prepare this file before running the installation steps below. You can start off with the following example (don't forget to replace the <placeholders>!) and modify it to your needs if necessary. Refer to :ref:`description_backend_config-label` for more information about all the configuration options.

.. warning::
   Please make sure to save 'sessionSecretKey' and 'smtpServer.password' in a secret way on your server! With the 'sessionSecretKey' a bad actor could log in as any user, even as an admin user, and read any current and future user data. With the 'smtpServer.password' a bad actor could authenticate with your mail server and send malicious phishing emails to you users while masquerading as the server admin.

In this setup, sessionSecretKey and the smtp password are being read from the environment variables 'PROJECT_W_JWT_SECRET_KEY' and 'PROJECT_W_SMTP_PASSWORD'. If you want you can also choose to set them here directly in the config, but if you do so please take appropriate measures to keep this config file secret!

.. code-block:: yaml

   clientURL: https://<DOMAIN>/#
   databasePath: /database
   loginSecurity:
     sessionSecretKey: !ENV ${JWT_SECRET_KEY}
   smtpServer:
     domain: <YOUR SMTP SERVERS DOMAIN>
     port: <SMTP PORT OF SMTP SERVER>
     secure: <starttls or ssl>
     senderEmail: <EMAIL ADDRESS>
     username: <probably same of above>
     password: !ENV ${SMTP_PASSWORD}

Choose between the following instructions depending on your setup. If you are unsure which setup to choose then :ref:`standalone_all-label` is probably for you.

.. _standalone_all-label:

Standalone, All-in-One
''''''''''''''''''''''

Additionally to the backend and frontend, the following instructions will also set up certbot to request let's encrypt ssl certificates. If you want to use your own certificates instead, please jump ahead to :ref:`standalone_byo-label`.

1. Install Docker: Refer to your distros package manager / the `Docker documentation <https://docs.docker.com/engine/install/>`_ for this
2. Create initial directory structure and enter project-w directory:

   .. code-block:: console

      mkdir -p project-W/project-W-data/sslCert && mkdir project-W/project-W-data/config && cd project-W

3. Put your config.yml into ./project-W-data/config
4. Put docker-compose.yml in the current directory. Use the following config and make same adjustments if needed (make sure to replace the <placeholders>!):

   .. code-block:: yaml

      services:
        backend:
          image: ghcr.io/julianfp/project-w_backend
          restart: unless-stopped
          volumes:
            - ./project-W-data/config:/etc/xdg/project-W/
            - ./project-W-data/database:/database
          environment:
            - JWT_SECRET_KEY=${PROJECT_W_JWT_SECRET_KEY:-}
            - SMTP_PASSWORD=${PROJECT_W_SMTP_PASSWORD:-}
        frontend:
          image: ghcr.io/julianfp/project-w_frontend
          restart: unless-stopped
          ports:
            - 80:80
            - 443:443
          volumes:
            - ./project-W-data/sslCert:/ssl:ro
            - ./acme:/acme
          environment:
            - NGINX_CONFIG=initial
            - SERVER_NAME=<DOMAIN>
        certbot:
          image: certbot/certbot:latest
          depends_on:
            - frontend
          command: >-
                   certonly --reinstall --webroot --webroot-path=/var/www/certbot
                   --email <YOUR EMAIL ADDRESS> --agree-tos --no-eff-email
                   -d <DOMAIN>
          volumes:
            - ./project-W-data/sslCert:/etc/letsencrypt/live/<DOMAIN>
            - ./acme:/var/www/certbot

5. Generate a JWT_SECRET_KEY that will be used to for generating Session Tokens. If you have python installed you can use the following command for this:

   .. code-block:: console

      python -c 'import secrets; print(secrets.token_hex())'

6. Run the containers. Replace <JWT Secret Key> and <Your SMTP Password> with the JWT_SECRET_KEY we generated before and the password of the SMTP Server you want to use respectively:

   .. code-block:: console

      PROJECT_W_JWT_SECRET_KEY="<JWT Secret Key>" PROJECT_W_SMTP_PASSWORD="<Your SMTP Password>" docker compose up -d

7. Check the logs of the certbot container and wait for 'Successfully received certificate.'. Use the following command for this:

   .. code-block:: console

      docker logs project-w-certbot-1

   If that line appears, then please replace 'initial' in your docker-compose.yml with 'ssl'. After that rerun the command in step 6. If an error is shown instead, then please verify your DNS and Firewall configuration and try again beginning from step 6. In the end, your containers should be up and running and your docker-compose.yml should look like this:

   .. code-block:: yaml

      services:
        backend:
          image: ghcr.io/julianfp/project-w_backend
          restart: unless-stopped
          volumes:
            - ./project-W-data/config:/etc/xdg/project-W/
            - ./project-W-data/database:/database
          environment:
            - JWT_SECRET_KEY=${PROJECT_W_JWT_SECRET_KEY:-}
            - SMTP_PASSWORD=${PROJECT_W_SMTP_PASSWORD:-}
        frontend:
          image: ghcr.io/julianfp/project-w_frontend
          restart: unless-stopped
          ports:
            - 80:80
            - 443:443
          volumes:
            - ./project-W-data/sslCert:/ssl:ro
            - ./acme:/acme
          environment:
            - NGINX_CONFIG=ssl
            - SERVER_NAME=<DOMAIN>
        certbot:
          image: certbot/certbot:latest
          depends_on:
            - frontend
          command: >-
                   certonly --reinstall --webroot --webroot-path=/var/www/certbot
                   --email <YOUR EMAIL ADDRESS> --agree-tos --no-eff-email
                   -d <DOMAIN>
          volumes:
            - ./project-W-data/sslCert:/etc/letsencrypt/live/<DOMAIN>
            - ./acme:/var/www/certbot

8. You may want to setup a cronjob or a systemd service with systemd timers to periodically restart the certbot container. Let's encrypt certificates are only valid for 90 days, so if you don't your certificate will expire!
9. You may want to set up some kind of backup solution. For this you just need to backup the project-W-data directory (which will include the database, your ssl certificate and your config.yml) and maybe your docker-compose.yml if you made changes to it.

.. _standalone_byo-label:

Standalone, BYO
'''''''''''''''

If you want to bring your own ssl certificate (e.g. self-signed or using some other acme setup), then this is the right setup for you.

1. Install Docker: Refer to your distros package manager / the `Docker documentation <https://docs.docker.com/engine/install/>`_ for this
2. Create initial directory structure and enter project-w directory:

   .. code-block:: console

      mkdir -p project-W/project-W-data/sslCert/ && mkdir project-W/project-W-data/config && cd project-W

3. Put your config.yml into ./project-W-data/config
4. Put your ssl certificate files into ./project-W-data/sslCert. The following files should be in that directory: fullchain.pem (ssl certificate), privkey.pem (ssl certificate private key) and chain.pem (ssl trusted certificate for OCSP stapling). If you use self-signed certificates then chain.pem and fullchain.pem will be the same.
5. Put docker-compose.yml in the current directory. Use the following config and make same adjustments if needed (make sure to replace the <placeholders>!):

   .. code-block:: yaml

      services:
        backend:
          image: ghcr.io/julianfp/project-w_backend
          restart: unless-stopped
          volumes:
            - ./project-W-data/config:/etc/xdg/project-W/
            - ./project-W-data/database:/database
          environment:
            - JWT_SECRET_KEY=${PROJECT_W_JWT_SECRET_KEY:-}
            - SMTP_PASSWORD=${PROJECT_W_SMTP_PASSWORD:-}
        frontend:
          image: ghcr.io/julianfp/project-w_frontend
          restart: unless-stopped
          ports:
            - 80:80
            - 443:443
          volumes:
            - ./project-W-data/sslCert:/ssl:ro
          environment:
            - NGINX_CONFIG=ssl
            - SERVER_NAME=<DOMAIN>

6. Generate a JWT_SECRET_KEY that will be used to for generating Session Tokens. If you have python installed you can use the following command for this:

   .. code-block:: console

      python -c 'import secrets; print(secrets.token_hex())'

7. Run the containers. Replace <JWT Secret Key> and <Your SMTP Password> with the JWT_SECRET_KEY we generated before and the password of the SMTP Server you want to use respectively:

   .. code-block:: console

      PROJECT_W_JWT_SECRET_KEY="<JWT Secret Key>" PROJECT_W_SMTP_PASSWORD="<Your SMTP Password>" docker compose up -d

8. You may want to set up some kind of backup solution. For this you just need to backup the project-W-data directory (which will include the database, your ssl certificate and your config.yml) and maybe your docker-compose.yml if you made changes to it.

With Reverse Proxy
''''''''''''''''''

Follow this guide if you want to run this behind a Reverse Proxy which takes care of SSL. Please really only use this if this is the case since with this setup the webserver of the container will be set up with HTTP only. With a proper Reverse Proxy setup this means that the traffic would stay unencrypted between Project-W backend/frontend server and Reverse Proxy, but then would be encrypted before sending it to the internet. If you were to run the following setup without a Reverse Proxy then all the communication between client and backend as well as possibly backend and runners would be send unencrypted through the internet including passwords, session tokens and user data!

.. attention::
   Make sure that your reverse proxy is properly configured to handle the upload of large files. The backend can handle files up to a size of 1GB, setting this to anything less in your reverse proxy will hinder the submission of jobs and present the user with possibly confusing error messages! We will not cover the configuration of the reverse proxy here, but for example if you use nginx you will want to set ``client_max_body_size 1g;`` in your config.

1. Install Docker: Refer to your distros package manager / the `Docker documentation <https://docs.docker.com/engine/install/>`_ for this
2. Create initial directory structure and enter project-w directory:

   .. code-block:: console

      mkdir -p project-W/project-W-data/config && cd project-W

3. Put your config.yml into ./project-W-data/config
4. Put docker-compose.yml in the current directory. Use the following config and make same adjustments if needed (make sure to replace the <placeholders>!):

   .. code-block:: yaml

      services:
        backend:
          image: ghcr.io/julianfp/project-w_backend
          restart: unless-stopped
          volumes:
            - ./project-W-data/config:/etc/xdg/project-W/
            - ./project-W-data/database:/database
          environment:
            - JWT_SECRET_KEY=${PROJECT_W_JWT_SECRET_KEY:-}
            - SMTP_PASSWORD=${PROJECT_W_SMTP_PASSWORD:-}
        frontend:
          image: ghcr.io/julianfp/project-w_frontend
          restart: unless-stopped
          ports:
            - 80:80
          environment:
            - NGINX_CONFIG=reverseProxy
            - SERVER_NAME=<DOMAIN>

5. Generate a JWT_SECRET_KEY that will be used to for generating Session Tokens. If you have python installed you can use the following command for this:

   .. code-block:: console

      python -c 'import secrets; print(secrets.token_hex())'

6. Run the containers. Replace <JWT Secret Key> and <Your SMTP Password> with the JWT_SECRET_KEY we generated before and the password of the SMTP Server you want to use respectively:

   .. code-block:: console

      PROJECT_W_JWT_SECRET_KEY="<JWT Secret Key>" PROJECT_W_SMTP_PASSWORD="<Your SMTP Password>" docker compose up -d

7. You may want to set up some kind of backup solution. For this you just need to backup the project-W-data directory (which will include the database, your ssl certificate and your config.yml) and maybe your docker-compose.yml if you made changes to it.

Runner
``````

Like for the backend you also need a config.yml file for the runner. Prepare this file before following the installation steps below. You can use the following example as a base (don't forget to replace the <placeholder>!) and modify it to your needs if necessary. Refer to :ref:`description_runner_config-label` for more information about all the configuration options of the runner.

.. warning::
   Please make sure to save 'runnerToken' in a secret way on your machine! Runner tokens are unique to each runner! With it a bad actor could log in to the backend as this runner and accept jobs of possibly any user including their audio files. If you accidentally leaked a token, immediately contact an administrator to have the token revoked. If you are the administrator, please refer to :ref:`revoke_a_runner-label` for how to do that.

In this setup, runnerToken is being read from the environment variable 'PROJECT_W_RUNNER_TOKEN'. If you want you can also choose to set it directly in the config, but if you do so please take appropriate measures to keep this config file secret!

.. code-block:: yaml

   backendURL: https://<DOMAIN>
   modelCacheDir: /models
   runnerToken: !ENV ${RUNNER_TOKEN}

The runner runs the whisper model and thus benefits greatly from running on a GPU, which we heavily recommend. This GPU should have at least 10GB of VRAM available, ideally a bit more. If you don't have a powerful enough GPU available though you can choose to also run it on CPU. Choose between the following instructions depending on your choice. Currently we have only instructions for NVIDIA GPUs using CUDA but it should also be possible to run this on an AMD GPU using ROCM (for this you are on your own though).

NVIDIA GPU
''''''''''

1. Install Docker: Refer to your distros package manager / the `Docker documentation <https://docs.docker.com/engine/install/>`_ for this

2. Install the NVIDIA container toolkit. Refer to the `NVIDIA toolkit documentation <https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html>`_ for this. Don't forget to restart your docker daemon afterwards.

3. Create initial directory structure and enter project-w directory:

   .. code-block:: console

      mkdir -p project-W/runner-config && mkdir project-W/runner-models && cd project-W

4. Put your config.yml into ./runner-config

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
            - RUNNER_TOKEN=${PROJECT_W_RUNNER_TOKEN:-}
          deploy:
            resources:
              reservations:
                devices:
                  - driver: nvidia
                    count: 1
                    capabilities: [gpu]

   .. note::
      Alternatively if you have a system with multiple GPUs and you want to have more control over which GPU gets allocated to the Runner, you can replace 'count: 1' above with 'count: all' and then select the GPU in the config.yml using the 'torchDevice' option. See :ref:`description_runner_config-label`.

6. Create a new Runner and obtain its runner token. Refer to :doc:`connect_runner_backend` for how to do that.

7. Run the container. Replace <Runner Token> with the runner token you obtained from the backend in the previous step:

   .. code-block:: console

      PROJECT_W_RUNNER_TOKEN="<Runner Token>" docker compose up -d

8. You may want to back up the runners config file (in ./runner-config) and the docker-compose.yml file if you made any changes to them. The ./runner-models directory contains all the whisper models that the runner will fetch automatically. You don't need to backup this directory but you can keep this directory around, copy it to other machines and share it between runners so that the runner doesn't need to spend time fetching these models anymore and so that if you have multiple runners on the same machine the models don't take up storage space multiple times!

CPU
'''

1. Install Docker: Refer to your distros package manager / the `Docker documentation <https://docs.docker.com/engine/install/>`_ for this


2. Create initial directory structure and enter project-w directory:

   .. code-block:: console

      mkdir -p project-W/runner-config && mkdir project-W/runner-models && cd project-W

3. Put your config.yml into ./runner-config

4. Put docker-compose.yml in the current directory. Use the following config and make adjustments if needed

   .. code-block:: yaml

      services:
        runner:
          image: ghcr.io/julianfp/project-w_runner
          restart: unless-stopped
          volumes:
            - ./runner-config:/etc/xdg/project-W-runner/
            - ./runner-models:/models
          environment:
            - RUNNER_TOKEN=${PROJECT_W_RUNNER_TOKEN:-}

5. Create a new Runner and obtain its runner token. Refer to :doc:`connect_runner_backend` for how to do that.

6. Run the container. Replace <Runner Token> with the runner token you obtained from the backend in the previous step:

   .. code-block:: console

      PROJECT_W_RUNNER_TOKEN="<Runner Token>" docker compose up -d

7. You may want to back up the runners config file (in ./runner-config) and the docker-compose.yml file if you made any changes to them. The ./runner-models directory contains all the whisper models that the runner will fetch automatically. You don't need to backup this directory but you can keep this directory around, copy it to other machines and share it between runners so that the runner doesn't need to spend time fetching these models anymore and so that if you have multiple runners on the same machine the models don't take up storage space multiple times!

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

Backend
```````

1. Install Python (3.8 or newer, we have tested 3.8 to 3.12) and pip
2. Clone this repository and enter it:

   .. code-block:: console

      git clone https://github.com/JulianFP/project-W.git & cd project-W

3. Install the package with pip:

   .. code-block:: console

      python -m pip install .

4. To run the backend server in production you need a webserver with WSGI support, for example gunicorn. Install gunicorn with pip:

   .. code-block:: console

      python -m pip install gunicorn

5. Run the backend server with gunicorn:

   .. code-block:: console

      gunicorn --bind <DOMAIN>:443 --certfile=<Path to ssl cert> --keyfile=<path to ssl key> project_W:create_app()

Frontend
````````

The frontend is written in Svelte and needs to be compiled into native Javascript. To do this you will need some build dependencies, however you can remove them after step 4. If you want you can even build it on a different machine and then just move the dist directory to the server between step 4 and 5.

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

4. Build the frontend (replace <BACKEND URL> with the url to the backend api. Leave empty if the frontend and backend are hosted on the same origin):

   .. code-block:: console

      VITE_BACKEND_BASE_URL="<BACKEND URL>" pnpm build

5. You can find the result in the ./dist directory. Setup a webserver (like nginx) to serve all contents of this directory. Optionally you can also setup nginx in a way such that it forwards requests to /api/* routes to the gunicorn webserver (which then should run on a different port without ssl). This way both backend and frontend would run on the same server and origin. Make sure to enable https!

Runner
``````

1. Install Python (3.11 or newer, we have tested 3.11 to 3.12), pip, and ffmpeg.
2. Clone this repository and enter it:

   .. code-block:: bash

      git clone https://github.com/JulianFP/project-W-runner.git & cd project-W-runner

3. Install the package with pip:

   .. code-block:: bash

      python -m pip install .

4. Set the relevant config values:

  For the runner to work, it needs a config as described in :ref:`description_runner_config-label`. You always need to set the ``backendURL`` and ``runnerToken`` values, otherwise the runner will abort on startup. Please refer to :doc:`connect_runner_backend` for how to do that.

.. warning::
   The tokens must be unique per runner and must be kept secret. If you accidentally leaked a token, immediately contact an administrator to have the token revoked. If you are the administrator, please refer to :ref:`revoke_a_runner-label` for how to do that.

5. Start up the runner:

   .. code-block:: bash

      python -m project_W_runner

6. You may want to make sure that the runner will always restart itself even if it crashes. Currently this might happen in rare cases, so maybe write a script or a systemd service that will always automatically restart the runner in case of a crash.
