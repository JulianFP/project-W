{
  self,
  stdenv,
  lib,
  nodejs_24,
  pnpm_10,
  writeShellScriptBin,

  #needs to be supplied explicitly
  backend_base_url ? "",
}:

stdenv.mkDerivation (finalAttrs: {
  pname = "project_W_frontend";
  version = "0.4.2";

  src = lib.fileset.toSource {
    root = ../frontend;
    fileset = ../frontend;
  };

  nativeBuildInputs = [
    nodejs_24
    pnpm_10.configHook
  ];

  buildInputs = [
    (writeShellScriptBin "git" ''
      if [ "$1" == "rev-parse" ]; then
        echo "${self.shortRev or self.dirtyShortRev}"
      else
        echo "v${finalAttrs.version}"
      fi
    '')
  ];

  pnpmDeps = pnpm_10.fetchDeps {
    inherit (finalAttrs) pname version src;
    fetcherVersion = 2;
    hash = "sha256-+2nJypUjjPwU/r9YBujO1Dj0yRNNsyJFwtXFUH59Q4w=";
  };

  buildPhase = ''
    ${pnpm_10}/bin/pnpm build
  '';

  installPhase = ''
    cp -r build $out
  '';

  PUBLIC_BACKEND_BASE_URL = backend_base_url;

  meta = {
    description = "Frontend files for Project-W";
    homepage = "https://github.com/JulianFP/project-W";
    license = lib.licenses.agpl3Only;
  };
})
