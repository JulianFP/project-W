Testing and code quality
========================

This document describes the current testing strategies and general measures to keep code quality up and its formatting consistent.

.. _test_setup-label:

Test setup
----------

Problems with standard component testing
````````````````````````````````````````

FastAPI does provide good tooling for testing the API in a more classical component test setup with pytest. For this application a setup like that would come with a significant amount of work and some serious shortcomings: The backend relies on many external services for its operations: A PostgreSQL database, a Redis database, a SMTP server, one or more runners and optionally LDAP and OIDC providers. These services wouldn't be available in a component test setup. The solution would be to replace all code that communicates with such services with dummy code during testing time. This could be done either by supplying a different class for database/caching operations that implements the same abstract parent class during testing time (both the PostgreSQL and Redis adapters inherit from an abstract parent class, it would 'just' require a dummy implementation of these classes) or my monkey patching. This has two major disadvantages:

- for so many services it would be a lot of work

- most of the backend's behavior and logic is actually implemented in these services. If all these services would be replaced by dummy implementations, there wouldn't remain much else to test for the component tests.

- these services, their behavior and correct interfacing by the backend is very crucial and should also be tested

Because of these considerations I chose to prioritize the system and Integration tests. For the time being there are no component tests of Project-W code.

System and Integration testing
``````````````````````````````

The goal of this test setup is to deploy a fully working version of Project-W including PostgreSQL, Redis, runners and more in a way that simulates a real world deployment as much as possible, and then use `pytest <https://docs.pytest.org>`_ and httpx to make http requests to the backend, effectively simulating a client. This test setup required the following to work:

GitHub actions as our CI system
```````````````````````````````

Github actions and Github runners are powerful enough to setup multiple docker containers, to build the Project-W container and the Project-W-runner container in it's dummy version (because the runner doesn't have enough storage for the full WhisperX version) and then run the pytest test suite.

This test is implemented as matrix test, meaning the same thing is done for each combination of Python version, PostgreSQL version and Redis version that I defined in the action (currently for each the oldest and newest supported by the backend).

In addition to that our CI system also runs `pre-commit.ci <https://pre-commit.ci>`_ for code formatting.

pytest fixtures
```````````````

The docker containers of the backend and runners are started and stopped using pytest fixtures. They also create their config files and flush the PostgreSQL and Redis databases afterwards. This ensures that each test case starts of with a freshly started backend and runner, and clean databases.

Test cases have some control over these fixtures over pytest's indirect parametrization feature (e.g. some of the contents of config files are handled this way).

.. _code_style-label:

Code style and formatting
-------------------------

We aim to have a consistent code styling to increase readability, maintainability and long-term for nicer git diffs. To ensure this we use `pre-commit <https://pre-commit.com/>`_ hooks. The ``.pre-commit-config.yaml`` file is ready in the root of all three repositories. Just install pre-commit on your system and run ``pre-commit install`` for each repository.

Python
``````

For python I use pre-commits own `check-python <https://github.com/pre-commit/pre-commit-hooks/blob/main/pre_commit_hooks/check_ast.py>`_, `check-builtin-literals <https://github.com/pre-commit/pre-commit-hooks/blob/main/pre_commit_hooks/check_builtin_literals.py>`_, `check-docstring-first <https://github.com/pre-commit/pre-commit-hooks/blob/main/pre_commit_hooks/check_docstring_first.py>`_ hooks as well as hooks for black and isort.

`black <https://github.com/psf/black>`_ is the most important one of these, it is a strict, opinionated code formatter. I set it up with the ``--line-length 100`` option to increase the allowed line length as I found the 79 character limit defined by `PEP8 <https://peps.python.org/pep-0008/>`_ to be too restrictive for this project. The point of this is to increase code readability, and having simple and straight forward if statements or prints to be stretched over multiple lines hurts this cause. I found 100 characters per line to be a good sweet spot. Other than that our code should be PEP8 compliant.

`isort <https://github.com/PyCQA/isort>`_ is responsible for sorting import statements. I set it up with ``--profile black`` to make it compatible with the black formatter.

Javascript/Typescript
`````````````````````

For the Javascript/Typescript code of the frontend I use `biome <https://biomejs.dev/>`_ to format the code. Biome is also configured to also check the script sections of all .svelte files to a certain degree however it will ignore any html/css. Most notably explicit usage of the ``any`` keyword is banned from the codebase among other things.
