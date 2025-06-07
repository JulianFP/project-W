{ lib, python313Packages }:

python313Packages.buildPythonPackage rec {
  pname = "project_W";
  version = "0.3.0";
  pyproject = true;

  src = ../../.;

  build-system = [ python313Packages.setuptools ];

  nativeBuildInputs = with python313Packages; [ setuptools-scm ];

  propagatedBuildInputs = with python313Packages; [
    click
    argon2-cffi
    itsdangerous
    fastapi
    pydantic
    email-validator
    psycopg
    psycopg-pool
    redis
    authlib
    pyjwt
    bonsai
    aiosmtplib
    granian
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
