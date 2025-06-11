{ lib, python3Packages }:

python3Packages.buildPythonPackage rec {
  pname = "project_W";
  version = "0.3.0";
  pyproject = true;

  src = ../../.;

  build-system = [ python3Packages.setuptools ];

  nativeBuildInputs = with python3Packages; [ setuptools-scm ];

  propagatedBuildInputs = with python3Packages; [
    click
    argon2-cffi
    fastapi
    pydantic
    email-validator
    psycopg
    psycopg-pool
    redis
    authlib
    pyjwt
    itsdangerous
    bonsai
    aiosmtplib
    granian
    setproctitle
    python-multipart
    httpx
    platformdirs
    pyaml-env
  ];

  pythonImportsCheck = [ pname ];

  #hardcode version so that setuptools-scm works without .git folder:
  SETUPTOOLS_SCM_PRETEND_VERSION = version;

  meta = {
    description = "Backend API server for Project-W";
    homepage = "https://github.com/JulianFP/project-W";
    license = lib.licenses.agpl3Only;
    mainProgram = pname;
  };
}
