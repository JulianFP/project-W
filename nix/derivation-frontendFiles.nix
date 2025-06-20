{
  lib,
  mkPnpmPackage,
  writeShellScriptBin,

  #needs to be supplied explicitly
  backend_base_url ? "",
}:

mkPnpmPackage rec {
  src = ../.;

  version = "0.3.0";

  distDir = "build";

  buildInputs = [
    (writeShellScriptBin "git" ''
      echo "v${version}"
    '')
  ];

  PUBLIC_BACKEND_BASE_URL = backend_base_url;

  meta = {
    description = "Frontend files for Project-W";
    homepage = "https://github.com/JulianFP/project-W-frontend";
    license = lib.licenses.agpl3Only;
  };
}
