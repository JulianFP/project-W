Installation
============

The following installation guides are for Linux only. Theoretically all the components of this software should be possible to deploy onto other operating systems as well however this is not tested and not supported. You will have to be on your own for that.

Docker
------

We provide a Dockerfile for each of the components of this software (client, backend, runner). The best way to use them is with Docker Compose. In the following we assume that you want to host our backend and client/frontend on the same server, and the runner on a different one. If this assumption doesn't hold for you (e.g. when you want the frontend to be served by a different server than the backends API), then you may have to write your own Dockerfiles and docker-compose.yml or choose a different installation method. 

Backend & Frontend
``````````````````

To run the backend you need a config.yml file that configures it. Prepare this file before running the installation steps below. You can start off with the following example (don't forget to replace the placeholders!) and modify it to your needs if necessary. Refer to <TODO> for more information about all the configuration options.

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

Choose between the following setups depending on your needs. Only follow one of them!

Standalone, all-in-one
''''''''''''''''''''''

Follow this guide if you don't have a Reverse Proxy and you want to have an all-in-one solution that requests and auto-renews the SSL certificate from Let's encrypt. 

Standalone, bring your own certificate
''''''''''''''''''''''''''''''''''''''

Follow this guide if you don't have a Reverse Proxy and you want to use your own SSL certificates (e.g. when you have your own CA or if you already have some kind of solution to get SSL certificates). 

1. Install Docker: Refer to your distros package manager / the Docker documentation for this
2. Create initial directory structure and enter project-w directory:

   .. code-block:: console

      mkdir -p project-W/project-W-data/sslCert && mkdir project-W/project-W-data/config && cd project-W

3. Put your .crt and .pem files of your ssl certificate into ./project-W-data/sslCert/
4. Put your config.yml into ./project-W-data/config
5. Put docker-compose.yml in the current directory. Use the following config and make same adjustments if needed:

   .. code-block:: yaml

      services:
        backend:
          build: https://github.com/JulianFP/project-W.git
          volumes:
            - ./project-W-data/config:/etc/xdg/project-W/
            - ./project-W-data/database:/database
          environment:
            - JWT_SECRET_KEY=${PROJECT_W_JWT_SECRET_KEY:-}
            - SMTP_PASSWORD=${PROJECT_W_SMTP_PASSWORD:-}
        frontend:
          build: https://github.com/JulianFP/project-W-frontend.git
          ports:
            - 80:80
            - 443:443
          volumes:
            - ./project-W-data/sslCert:/sslCert
          environment:
            - SERVER_NAME="localhost"

6. Generate a JWT_SECRET_KEY that will be used to for generating Session Tokens. If you have python installed you can use the following command for this:

   .. code-block:: console

      python -c 'import secrets; print(secrets.token_hex())'

7. Build and run the containers. Replace <JWT Secret Key> and <Your SMTP Password> with the JWT_SECRET_KEY we generated before and the pasword of the SMTP Server you want to use respectively:

   .. code-block:: console

      PROJECT_W_JWT_SECRET_KEY="<JWT Secret Key>" PROJECT_W_SMTP_PASSWORD="<Your SMTP Password>" docker compose up -d

8. You may want to setup a systemd service or similar to start the containers automatically. Please be careful with where you store your JWT Secret Key and your SMTP Password, they should always stay secret!
9. You may want to setup some kind of backup solution. For this you just need to backup the project-W-data directory (which will include the database, your ssl certificate and your config.yml) and maybe your docker-compose.yml if you made changes to it.

With Reverse Proxy
''''''''''''''''''

Follow this guide if you want to run this behind a Reverse Proxy which takes care of SSL. Please really only use this if this is the case since the webserver will be set up with HTTP only. If you have a Reverse Proxy this means that the traffic would stay unencrypted between Project-W backend/frontend server and Reverse Proxy, but then would be encrypted before sending to the internet. If you were to run the following setup without a Reverse Proxy then all the communation between client and backend as well as possibly backend and runners would be send unencrypted through the internet including passwords, session tokens and user data!

Runner
``````

NixOS
-----

Manual installation
-------------------

You can also run Project-W barebones. This can be a bit more difficult and the following steps will not be as detailed as the ones with Docker or NixOS. You will have to do stuff like configuring python virtual environments, setting up webservers or compiling the frontend yourself.

Backend
```````

1. Install Python (3.8 - 3.11 are tested to work) and pip
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
