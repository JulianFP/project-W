Config Files
============

Both the backend and the runner are configured with a YAML config file each. The handling of the config files is the same, just the content (available attributes) is different.

File type and location
----------------------

.. note::
   This applies to both the backend and the runner. For the runner config just replace `project-W` with `project-W-runner` in the paths.

A config file has to be named `config.yml`. It can be in one of the following directories. They follow the `XDG Base Directory Specification <https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html>`_ under Linux):

1. User config path: Under Linux this is `$XDG_CONFIG_HOME/project-W` (which usually is `~/.config/project-W`)
2. Site config path: Under Linux this is the first entry of `$XDG_CONFIG_DIRS` concatenated with `/project-W` (which usually is `/etc/xdg/project-W`)
3. The source directory of the `project_W` python package (to be more specific: the directory that also contains the `config.py` module)
4. The current working directory (i.e. the directory from which you start the program)

These directories are searched in this order, and the first directory that contains a file called `config.yml` will be chosen. This means that for example a user can overwrite a system-wide configuration (in `/etc/xdg/project-W`) by putting their own config file into `~/.config/project-W`.

Loading config attributes from environment variables
----------------------------------------------------

This works for both the backend and the runner.

Instead of explicitly entering static variables into the config file, you can also choose to dynamically load the value of a variable from the programs environment at startup time. This is especially useful if you don't want to write secrets like the sessionSecretKey the smtp password or the runner token directly into the config file (e.g. if you keep your config files public).

To do use the `!ENV` Tag followed by the env var you want to load from with a dollar sign and curly brackets. For example if you want to load loginSecurity.sessionSecretKey from the env var `JWT_SECRET_KEY`, then you would write the following into your config file:

   .. code-block:: YAML

      loginSecurity:
        sessionSecretKey: !ENV ${JWT_SECRET_KEY}

If you want you can also define a default value in case the env var isn't defined by using a colon. For example if you want signups to be possible by default but you want to be able to disable them temporarily by setting the env var `DISABLE_SIGNUP` to `true` then you could write the following:

   .. code-block:: YAML

      loginSecurity:
        disableSignup: !ENV ${DISABLE_SIGNUP:false}

For a full reference of the syntax and usage of this feature please refer to `the readme of pyaml-env <https://pypi.org/project/pyaml-env/>`_ which we use to do this.

.. _description_backend_config-label:

Description of backend config options
-------------------------------------

The following table gives an overview over all options available to you. All options printed in bolt letters must be set since they do not have any default value, however you probably also want to set 'loginSecurity.sessionSecretKey'. For an example config, please refer to :ref:`docker_backend_frontend-label`

.. jsonschema:: project_W.config.schema
   :hide_key: /**/pattern,/**/additionalProperties
   :hide_key_if_empty: /**/default

Description of runner config options
-------------------------------------

TODO
