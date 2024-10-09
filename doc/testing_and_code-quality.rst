Testing and code quality
========================

This document describes the current testing strategies and general measures to keep code quality up and its formatting consistent.

.. _test_setup-label:

Test setup
----------

Currently the backend has rigorous component tests for all client-facing api routes (meaning all ``/api/jobs`` and ``/api/users`` routes, refer to :ref:`general-label` for more info about them). These tests can be found in the ``/tests`` directory.

The test framework in use is ``pytest`` and we have multiple custom fixtures around it. Most notably there is a ``client`` fixture that uses flasks ``app.test_client()`` to mock an http client that then calls the api routes in the test cases and also creates the config file which is required to run most of the backends code. There is also a ``mockedSMTP`` fixture that mocks pythons smtp library and is required for testing routes that would otherwise send emails to the user. These fixtures are defined in ``/tests/conftest.py``

Backend fixtures
````````````````

The ``client`` fixture accepts multiple non-optional parameters which are meant to define config options that affect the behavior of certain api-routes. Think of them as parameters of a function that you write a test for: We want to write one test case for every possible parameter value or maybe even for every possible combination of parameter values. Luckily, pytest does that for us: We can write a test case ones and define multiple tuples of parameters that the config should have in the ``@pytest.mark.parametrize``. Pytest will then run that test case multiple times, ones for each tuple of config parameters.

The ``@pytest.mark.parametrize`` should look like this when using the ``client`` fixture: As the first parameter, pass the name of the fixture as a string (`"client"`). As the second parameter, pass an array of tuples of config file parameters. Each tuple in the array is one combination of config file parameters (pytest will run the test case for each of these tupels ones). Both values of the tupel are strings and should contain valid json for the config options ``allowedEmailDomains`` and ``disableSignup`` (refer to :ref:`description_backend_config-label` for more info about them). All other config values are also being set by the fixture but currently not customizable on a per test case basis. Go to ``/tests/conftest.py`` to find out their values. Also don't forget to set ``indirect=True`` to activate this feature. After that you can define the test case in usual pytest notation. Don't forget to include the ``client`` fixture as well as other fixtures you want to use (e.g. ``mockedSMTP``) as function parameters.

Take the following test case definition as an example:

   .. code-block:: python

      @pytest.mark.parametrize(
         "client",
         [("[]", "false"), ("[ 'test.com' ]", "false"), ("[ 'test.com', 'sub.test.com' ]", "false")],
         indirect=True,
      )
      def test_signup_valid(client: Client, mockedSMTP):

This tests a valid call of the signup route. It instructs pytest to run the test case three times: The first time all mail domains are allowed, the second time only test.com is allowed, and the third time both test.com and sub.test.com are allowed. In all three instances, signup stays enabled. In addition to the client fixture this test case also requests the mockedSMTP fixture because the signup route sends an activation email to the user.

For more examples of how to use these fixtures, look at existing test cases in ``/tests``.

CI setup
````````

We use Github actions and `pre-commit.ci <https://pre-commit.ci>`_ as our CI tools. When triggered it will validate that the following runs successfully:

- checkout the repository, install the package (with optional tests dependencies) using pip and run all pytest test cases (backend)

   - For each of the following systems: ubuntu-latest, macos-latest, windows-latest
   - For Python version 3.8 and version 3.12

- Measure the codecov test coverage for regressions (backend)

- run the pre-commit checks and apply changes (if any) in an automated commit (all repositories)

The CI will run for each newly pushed commit to the main branch as well as on open pull requests into the main branch. Issues discovered by the CI should be fixed before merging into main!

Shortcomings and planned improvements
`````````````````````````````````````

On the backend, the ``/api/runners`` routes currently don't have any test cases. The blocker for this is the requirement for a new fixture that mocks the runner somehow. It would also be nice to have dedicated test cases for some of the functions in utils.py, model.py and runner_manager.py independently from the api interface to get the coverage even higher. This would require additional fixtures as well (e.g. for checking database writes).

On the frontend and runner side we currently don't have any automated tests. The runner has a working pytest and Github CI setup similar to the one of the backend, however it would also require additional fixtures (e.g. for mocking the backend) to be able to actually define test cases.

It is planned to remedy these shortcomings. There are open Github issues for them, check them for progress on this.

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
