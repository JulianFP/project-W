Technology stack
================

Please read the introduction first since it also includes the explanation of the general architecture of the project: :doc:`intro`

The Backend
-----------

The backend is written in Python and uses the `FastAPI framework <https://fastapi.tiangolo.com/>`_ to build the REST API. For more information about the API refer to :doc:`api`.

All permanent information about users, jobs and runners are stored in a `PostgreSQL <https://www.postgresql.org/>`_ database. I use `psycopg <https://www.psycopg.org/psycopg3/>`_ to interface with Postgres from the Python backend.

Project-W is written to be deployable in a `Kubernetes <https://kubernetes.io/>`_ or Kubernetes-like environment where multiple instances of the backend are running at the same time (called pods in Kubernetes) and the user traffic is split among these instances. Because of this the backend can't have any application state that persists for longer than the processing of one http request or wasn't derived from the config file or any other shared external source. To achieve this I use `Redis <https://redis.io/>`_ as a caching solution for temporary data in addition to PostgreSQL which stores the more permanent data. This temporary data includes a list of all online runners and their attributes, the jobs that are currently being processed, an event system for server-sent events (SSE) and more. I use the official `python redis library <https://pypi.org/project/redis/>`_ to interface with the Redis database.

Another important design decision is that all code was written from the ground up in an asynchronous manner using asyncio. FastAPI is an ASGI (Asynchronous Server Gateway Interface) framework, meaning that in contrary to WSGI (Web Server Gateway Interface) frameworks like Flask the handling of http requests happens asynchronously. To take advantage of this all other code that is being called from an http request handler function is also asynchronous, including communication with PostgreSQL, with Redis, with the SMTP server for sending mails (for which I use the `aiosmtplib library <https://pypi.org/project/aiosmtplib/>`_) as well as LDAP queries (for which I use the `bonsai library <https://pypi.org/project/bonsai/>`_).

The backend also makes heavy use of `Pydantic <https://pydantic.dev>`_ for validating all input and output data of http requests as well as data coming from PostgreSQL and Redis. Pydantic also takes care of validating the contents of the yaml config file after it has been parsed by the pyaml-env library (which takes environment variables into account). Some Pydantic models are also shared between the runner and the backend.

User authentication is done using the `Argon2 <https://pypi.org/project/argon2-cffi/>`_ hasher which is recommended by the OWASP. After initial authentication (using their password) users get a JWT Token which will be used for authentication in subsequent api calls. To validate these tokens I use `PyJWT <https://pypi.org/project/PyJWT/>`_. For communicating with OIDC identity providers and validating OIDC id_tokens I use the `authlib library <https://authlib.org/>`_.

The whole ASGI application is then being served using `granian <https://pypi.org/project/granian/>`_. I chose granian over more standard alternatives like uvicorn because of it's performance and support for HTTP/2. The latter is especially useful for the use with server-sent events because for these the frontend may keep multiple connections to the backend open at the same time and the limit for concurrent HTTP connections is very low when using HTTP/1.1 (in Chrome it is 6 connections per browser instance, not even per browser tab). Granian is called from within Python so that it can be easily configured over the config file (e.g. SSL certificates, number of workers, ...).

The backend is started using the `Project_W` cli built with `click <https://click.palletsprojects.com>`_. The CLI includes some extra options like setting the path to the config file or starting the backend in development/debug mode.

The Runners
-----------

The runner is also written in Python and does the actual transcription using OpenAIs open-source Python whisper package.

One runner cannot do more than one job at a time. If you want to increase the throughput by parallelization just add more runners since a backend can handle as much runners as you want.

The communication between runner and backend always goes from the runner to the backend, never the other way around (i.e. the runner will always initialize the communication). The backend is the http-server, while the runner is the http-client. The runner uses the asyncio and `httpx <https://www.python-httpx.org/>`_ libraries for this. It has two major advantages:

- The runner doesn't need a publicly reachable IP-address and no special firewall settings or similar (it can run behind a nat and a company firewall if you wan't). It just needs to be able to reach the backend.
- The runner doesn't need a certificate or key-pair for encryption. As long as the backend has an ssl certificate, the communication between backend and runner will be automatically https encrypted

Each runner send a heartbeat to the backend periodically (currently every 15 seconds). If the backend assigned a job to this runner, it will notify it through the heartbeats response. After that the runner will download the job from the backend and process it. During processing it will send the current progress status to the backend in its heartbeats. After finishing it will upload the transcript to the backend.

The runner authenticates to the backend using *runner tokens*. You can create them using the /api/admins/create_runner api route of the backend. Refer to :ref:`get_a_runner_token-label` for how to exactly do that. Each runner has a unique token and the backend uses them for example to send them the correct job data.

The runner validates the data it receives using Pydantic similar to how the backend does it, but from the client's perspective. The parsing of the config file happens the same way as on the backend, using Pydantic and pyaml-env.

The actual transcription is done using the `WhisperX package <https://pypi.org/project/whisperx/>`_ and some custom monkeypatches on top of it. WhisperX offers higher transcription speeds and more features like alignment and diarization compared to OpenAI's official Whisper package.

The runner also started through a click CLI similar to the one of the backend. It includes a dummy option to start it in a dummy mode where instead of using WhisperX to transcribe the received audio it will just simulate a transcription and always return some example test (useful for testing).

The Frontend
------------

The Frontend is a SPA written in the Javascript-Framework `Svelte <https://svelte.dev/>`_ and it's application framework SvelteKit. I chose Svelte because it is easy to learn and use and its code is nice and compact. Also Svelte is compiled into native Javascript meaning that I do not need to ship a runtime environment to the user which decreases the package size a lot. I opted to use Typescript to get some type-safety and to quickly identify potential issues before even running the code.

SvelteKit is currently set up with the static adapter and with the hash-based router type. This means that the application is built to static files that then can be shipped by any webserver (in our case granian, the one used in our backend) and doesn't require nodejs or anything else on the server-side.

I made heavy use of the `flowbite-svelte <https://flowbite-svelte.com/>`_ UI-component library (as you can see in the result since I didn't bother to change the color scheme from the default). Most if not all components of the frontend are from this library. I also used `flowbite-svelte-icons <https://flowbite-svelte.com/docs/extend/icons>`_ for the Icons. This also means that the CSS-framework `tailwindcss <https://tailwindcss.com/>`_ is a big part of the project since flowbite makes heavy use of it. It makes writing CSS a lot easier and more convenient through the pre-made CSS-classes it provides.

All the dependencies of the project are managed using the `pnpm Package Manager <https://pnpm.io/>`_. It was the recommended way to use flowbite-svelte and offers some nice benefits over npm (like being faster and more efficient). The used package versions are version-locked in the ``pnpm-lock.yaml`` file in the root of the repository. If strongly recommend using pnpm and this lock-file since else you might not get the same versions of all the dependencies we used which might result in a different result than intended or maybe even not compiling code (especially flowbite-svelte is under constant development).
