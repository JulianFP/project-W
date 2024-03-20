{
  lib,
  mkPnpmPackage,

  #needs to be supplied explicitly
  backend_base_url ? ""
}:

mkPnpmPackage {
  src = ../.;
  VITE_BACKEND_BASE_URL = backend_base_url;
  meta = {
    description = "Frontend files for Project-W";
    homepage = "https://github.com/JulianFP/project-W-frontend";
    license = lib.licenses.mit;
  };
}
