{
  lib,
  mkPnpmPackage,
  writeShellScriptBin,
  self,

  #needs to be supplied explicitly
  backend_base_url ? "",
}:

mkPnpmPackage rec {
  src = ../frontend;

  version = "0.3.0";

  distDir = "build";

  buildInputs = [
    (writeShellScriptBin "git" ''
      if [ "$1" == "rev-parse" ]; then
        echo "${self.shortRev or self.dirtyShortRev}"
      else
        echo "v${version}"
      fi
    '')
  ];

  PUBLIC_BACKEND_BASE_URL = backend_base_url;

  meta = {
    description = "Frontend files for Project-W";
    homepage = "https://github.com/JulianFP/project-W-frontend";
    license = lib.licenses.agpl3Only;
  };
}
