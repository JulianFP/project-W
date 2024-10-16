{ lib, python3Packages }:

python3Packages.buildPythonPackage rec {
  pname = "project_W";
  version = "0.0.1";
  format = "setuptools";

  src = ../../.;

  nativeBuildInputs = with python3Packages; [ setuptools-scm ];
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

  nativeCheckInputs = with python3Packages; [
    pytestCheckHook
    pytest-mock
    pytest-cov
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
