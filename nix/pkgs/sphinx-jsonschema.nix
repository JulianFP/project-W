{
  lib,
  fetchPypi,
  python3Packages
}:

python3Packages.buildPythonPackage rec {
  pname = "sphinx-jsonschema";
  version = "1.19.1";
  src = fetchPypi {
    inherit version;
    pname = "sphinx-jsonschema";
    sha256 = "sha256-sjhf4ces8udZFSrv7QyxfJIGRbKnXJk0AAycUo59U8E=";
  };
  propagatedBuildInputs = with python3Packages; [
    docutils
    requests
    jsonpointer
    pyyaml
  ];
  meta = {
    description = "A Sphinx extension to display a JSON Schema ";
    homepage = "https://github.com/lnoor/sphinx-jsonschema";
    license = lib.licenses.gpl3Only;
  };
}
