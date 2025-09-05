{
  lib,
  fetchPypi,
  python3Packages,
}:

python3Packages.buildPythonPackage rec {
  pname = "autodoc-pydantic";
  version = "2.2.0";
  format = "wheel";

  src = fetchPypi {
    inherit version;
    pname = "autodoc_pydantic";
    format = "wheel";
    dist = "py3";
    python = "py3";
    sha256 = "sha256-jGo2+/btJwDqnG0h6natVBtiH73xa1qA7gRnNUivTZU=";
  };

  propagatedBuildInputs = with python3Packages; [
    sphinx
    pydantic
    pydantic-settings
    importlib-metadata
  ];

  meta = {
    description = "Seamlessly integrate pydantic models in your Sphinx documentation.";
    homepage = "https://github.com/mansenfranzen/autodoc_pydantic";
    license = lib.licenses.mit;
  };
}
