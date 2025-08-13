Development - Getting started
=============================

.. note::
   Before contributing code please also read :ref:`code_style-label` for the guidelines we use for code styling in this project and :ref:`test_setup-label` for how to write test cases for your code.

This is a guide for how to get a basic Project-W development environment up and running. Please also refer to :ref:`manual_installation-label` for additional instructions (however focused on deployment).

Setup instructions
------------------

Backend
```````

1. You have to have Python, pip and git installed. The project is written to be compatible with Python 3.11 and newer however we mostly used Python 3.12 and 3.13 during development.

2. Clone the repository and enter it

   .. code-block:: console

      git clone https://github.com/JulianFP/project-W.git && cd project-W

3. Set up a python virtual environment

   .. code-block:: console

      python -m venv venv

4. Activate virtual environment

   .. code-block:: console

      source venv/bin/activate

5. Install project dependencies including optional dependencies for testing and building the documentation:

   .. code-block:: console

      python -m pip install .[development_mode,docs]

You are now ready to go!

Frontend
````````

1. You have to have nodejs, pnpm and git installed. We used nodejs 24 for development.

2. Clone the repository and enter it

   .. code-block:: console

      git clone https://github.com/JulianFP/project-W-frontend.git && cd project-W-frontend

3. Install project dependencies with pnpm:

   .. code-block:: console

      pnpm install

You are now ready to go!

Runner
``````

1. You must have Python, pip and git installed. Additionally, you must have ffmpeg installed and in your ``$PATH``.
2. Clone the repository and enter it

   .. code-block:: bash

      git clone https://github.com/JulianFP/project-W-runner.git && cd project-W-runner

3. Set up a python virtual environment

   .. code-block:: bash

      python -m venv venv

4. Activate virtual environment

   .. code-block:: bash

      source venv/bin/activate

5. Install project dependencies including optional dependencies for testing. If you want to not only run the dummy runner but also the whisperx code then you also need to install the ``not_dummy`` optional dependencies:

   .. code-block:: bash

      python -m pip install .[tests]

You are now ready to go! Note that by default, Whisper caches downloaded models in ``$HOME/.cache/whisper/``. If you would like
the runner to download the models into a different directory, set ``whisper_settings.model_cache_dir`` in your ``config.yml`` to the desired directory.

.. _nix_develop-label:

Alternatively: Nix
``````````````````

If you have Nix installed you can set up your development environment with just one command (you don't have to use NixOS for this, you just need Nix). This will also set up pre-commit for you. You can use the same process for all three components of the project:

Clone the repository and enter its directory. After that run

   .. code-block:: console

      nix develop

You can also use `Direnv <https://github.com/nix-community/nix-direnv>`_ using `use flake` to do this automatically every time you enter the directory.

Usage instructions
------------------

Backend
```````

The easiest way to start a development instance of the backend is to use the provided `run.sh` script:

   .. code-block:: console

      ./run.sh

If you didn't set up a `config.yml` file before then it will use the provided dummy file that came with the git repository. This file is for development purposes only and should not be used in production! If you need to develop stuff that involves sending emails then you might want to adjust the file to incorporate a smtp configuration. Refer to :ref:`description_backend_config-label` for how to do that.

The backend will now run under the url `http://localhost:5000`, with the API docs available under `http://localhost:5000/docs`. The development webserver will also restart automatically when making changes to any code.

Frontend
````````

You can start a development server:

   .. code-block:: console

      pnpm dev

Now you can access the website over the url `http://localhost:5173` in your browser of choice and use the browsers development tools for debugging. The development server also supports hot module reloading which means that it will seamlessly update components on the website after you made changes to it without you even having to refresh the site in the browser.

The development build variables are declared in the file `.env.development`. We currently just have one variable: `VITE_BACKEND_BASE_URL`. It defines the url of the backend that the frontend should use. If it is not defined then the frontend will assume that the backend is hosted on the same origin than the frontend. The default value is set to the port under which the development server of the backend runs per default (on the same machine). You can also set/overwrite this by setting an environment variable in your terminal.

If you want to compile the project into raw HTML, CSS and Javascript files  then run

   .. code-block:: console

      pnpm build

It will output those files into the `dist` directory. If you plan on serving these on a different origin than the backend then you want to set `VITE_BACKEND_BASE_URL` to the backends url before building. Either do this in the terminal as an environment variable or create a file `.env.production` to set it more permanently.

Runner
``````

You can use the ``run.sh`` script to start the runner:

   .. code-block:: bash

      ./run.sh

Note that the runner will exit immediately if you don't provide a valid runner token as returned by ``/api/runners/create`` or if it can't access the backend at the provided URL. For more info on the runner configuration, refer to :ref:`description_runner_config-label`.

Alternatively if you don't want to run the whisperx component of the runner you can also add the `--dummy` CLI option to the command inside `run.sh`. This will result in the runner not doing any actual transcribing but can be a good option for testing purposes.
