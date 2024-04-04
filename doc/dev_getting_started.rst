Development - Getting started
=============================

This is a guide for how to get a basic Project-W development environment up and running. Please also refer to :ref:`manual_installation-label` for additional instructions (however focused on deployment).

Setup instructions
------------------

Backend
```````

1. You have to have Python, pip and git installed. The project is written to be compatible with Python 3.8 and newer however we mostly used Python 3.11 during development.
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

      python -m pip install .[tests,docs]

You are now ready to go! 

Frontend
````````

1. You have to have nodejs, pnpm and git installed. We used nodejs 20 and 21 for development.
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

5. Install project dependencies including optional dependencies for testing and building the documentation:

   .. code-block:: bash

      python -m pip install .[tests,docs]

You are now ready to go! Note that by default, Whisper caches downloaded models in ``$HOME/.cache/whisper/``. If you would like
the runner to download the models into a different directory, set ``modelCacheDir`` in your ``config.yml`` to the desired directory.

Alternatively: Nix
``````````````````

If you have Nix installed you can set up your development environment with just one command (you don't have to use NixOS for this, you just need Nix). You can use the same process for all three components of the project (TODO: not for runner yet): 

Clone the repository and enter its directory. After that run 

   .. code-block:: console
         
      nix develop

You can also use `Direnv <https://github.com/nix-community/nix-direnv>`_ using `use flake` to do this automatically every time you enter the directory.

Usage instructions
------------------

Backend
```````

You can run the project using its CLI interface with the command `project_W`. However this can become cumbersome for development purposes since you would have to run the pip install command after every change before you can test it. Instead you can use the `run.sh` script to start the flask app without having to do that:

   .. code-block:: console

      ./run.sh

If you didn't set up a `config.yml` file before then it will use the provided dummy file that came with the git repository. This file is for development purposes only and should not be used in production! If you need to develop stuff that involves sending emails then you might want to adjust the file to incorporate a smtp configuration. Refer to :ref:`description_backend_config-label` for how to do that.

The backend will now run under the url `http://localhost:5000`. The development flask webserver will also restart automatically when making changes.

Frontend
````````

You can start a development server:

   .. code-block:: console

      pnpm dev

Now you can access the website over the url `http://localhost:5173` in your browser of choice and use the browsers development tools for debugging. The development server also supports hot module reloading which means that it will seamlessly update components on the website after you made changes to it without you even having to refresh the site in the browser.

The development build variables are declared in the file `.env.development`. We currently just have one variable: `VITE_BACKEND_BASE_URL`. It defines the url of the backend that the frontend should use. If it is not defined then the frontend will assume that the backend is hosted on the same origin than the frontend. The default value is set to the port under which the development server of the backend runs per default (on the same machine). You can also set/overwrite this by setting an environment variable in your terminal.

If you want to compile the project into raw HTML, CSS and Javscript files  then run

   .. code-block:: console

      pnpm build

It will output those files into the `dist` directory. If you plan on serving these on a different origin than the backend then you want to set `VITE_BACKEND_BASE_URL` to the backends url before building. Either do this in the terminal as an environment variable or create a file `.env.production` to set it more permanently.

Runner
``````

You can use the ``run.sh`` script to start the runner:

   .. code-block:: bash

      ./run.sh

Note that the runner will exit immediately if you don't provide a valid runner token as returned by ``/api/runners/create`` or if it can't access the backend at the provided URL. For more info on the runner configuration, refer to :ref:`description_runner_config-label`.