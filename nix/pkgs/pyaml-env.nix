{
  lib,
  fetchPypi,
  python3Packages
}:

python3Packages.buildPythonPackage rec {
  pname = "pyaml-env";
  version = "1.2.1";
  src = fetchPypi {
    inherit version;
    pname = "pyaml_env";
    sha256 = "sha256-bV3JjIyC33Q6EywZbnmWMFDJ/rBbCm8l8613dx09lbA=";
  };
  doCheck = false;
  propagatedBuildInputs = with python3Packages; [
    pyyaml
  ];
  meta = {
    description = "Parse YAML configuration with environment variables in Python";
    homepage = "https://github.com/mkaranasou/pyaml_env";
    license = lib.licenses.mit;
  };
}
