{
  lib,
  python3Packages
}:

python3Packages.buildPythonPackage rec {
  pname = "project-W";
  version = "0.0.1";
  pyproject = true;
  src = ../../.;
  nativeBuildInputs = with python3Packages; [
    setuptools
    setuptools-scm
  ];
  propagatedBuildInputs = with python3Packages; [
    argon2-cffi
    click
    flask
    flask-jwt-extended
    flask-sqlalchemy
    flask-cors
    platformdirs
    pyaml-env
    jsonschema
  ];
  #hardcode version so that setuptools-scm works without .git folder:
  SETUPTOOLS_SCM_PRETEND_VERSION = version; 
  meta = {
    description = "Backend API server for Project-W";
    homepage = "https://github.com/JulianFP/project-W";
    license = lib.licenses.mit;
  };
}
