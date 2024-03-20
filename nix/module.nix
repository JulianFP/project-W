inputs: {config, lib, pkgs, ...}: 
let
  inherit (lib)
    mdDoc
    mkIf
    mkOption
    mkEnableOption
    mkDefault
    types
    optionalAttrs
    ;
  inherit (pkgs.stdenv.hostPlatform) system;
  cfg = config.services.project-W-frontend;
  cfg_str = "services.project-W-frontend";
in {
  options = {
    services.project-W-frontend = {
      enable = mkEnableOption (mdDoc "Frontend of Project-W");
      package = mkOption {
        type = types.package;
        default = pkgs.callPackage ./derivation-frontendFiles.nix {
          mkPnpmPackage = inputs.pnpm2nix-nzbr.packages.${system}.mkPnpmPackage;
          backend_base_url = cfg.backendBaseURL;
        };
        description = mdDoc ''
          Frontend files to use (index.html, javascript and css files). Note that setting this option to anything other than the default will result in [backendBaseURL](${cfg_str}.backendBaseURL) not working anymore. If you want to set it you will have to take care of that yourself since this config is set during build time of the package.
        '';
      };
      hostName = mkOption {
        type = types.singleLineStr;
        description = mdDoc ''
          FQDN for the project-W frontend instance.
        '';
      };
      backendBaseURL = mkOption {
        type = types.singleLineStr;
        default = "";
        description = mdDoc ''
          URL of backend api server that the frontend should use (without paths like /api). If set to an empty string, then the frontend will use the same origin under which it is hosted (do this if you want serve the frontend and backend with the same webserver).
        '';
      };
    };
  };

  config = mkIf cfg.enable {
    #setup nginx to serve requests
    services.nginx = {
      enable = mkDefault true;
      recommendedOptimisation = mkDefault true;
      recommendedProxySettings = mkDefault true;

      virtualHosts.${cfg.hostName}.root = cfg.package;
    };
  };
}
