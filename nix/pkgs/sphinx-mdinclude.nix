{
  lib,
  fetchPypi,
  python3Packages,
}:

python3Packages.buildPythonPackage rec {
  pname = "sphinx-mdinclude";
  version = "0.6.2";
  format = "pyproject";
  src = fetchPypi {
    inherit version;
    pname = "sphinx_mdinclude";
    sha256 = "sha256-RHRi6Cy4vmFASiIEIn+SB2nrkj0vV2COMyXzu4goa0w=";
  };
  nativeBuildInputs = with python3Packages; [
    flit-core
  ];
  propagatedBuildInputs = with python3Packages; [
    mistune
    docutils
    pygments
    sphinx
  ];
  nativeCheckInputs = with python3Packages; [
    pytestCheckHook
  ];
  meta = {
    description = "Sphinx extension for including or writing pages in Markdown format";
    homepage = "https://github.com/omnilib/sphinx-mdinclude";
    license = lib.licenses.mit;
  };
}
