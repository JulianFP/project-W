{
  config,
  lib,
  pkgs,
  ...
}:
let
  yamlFormat = pkgs.formats.yaml { };
  cfg = config.services.project-W;
  cfg_str = "services.project-W-backend";
in
{
  options = {
    services.project-W = {
      enable = lib.mkEnableOption ("Backend & Frontend of Project-W");
      package = lib.mkOption {
        type = lib.types.package;
        default = pkgs.python313Packages.project-W;
        description = ''
          Project-W python package to use.
        '';
      };
      frontend_package = lib.mkOption {
        type = lib.types.package;
        default = pkgs.project-W-frontend;
        description = ''
          Project-W frontend package containing compiled static files to use.
        '';
      };
      user = lib.mkOption {
        type = lib.types.singleLineStr;
        default = "project-W";
        description = ''
          User account under which project-W runs.
        '';
      };
      group = lib.mkOption {
        type = lib.types.singleLineStr;
        default = "project-W";
        description = ''
          User group under which project-W runs. This is for the service and flask stuff, the socket for communication between this service and nginx will always be set to [services.nginx.group](config.services.nginx.group) regardless.
        '';
      };
      settings = lib.mkOption {
        type = yamlFormat.type;
        description = ''
          The contents of the backend config as a Nix expression. Will be formatted into Yaml. Please don't put any sensitive information in here as it will be world-readable in the Nix store! Use the !ENV notation as described in the Project-W documentation (inside a string in Nix).
        '';
      };
      envFile = lib.mkOption {
        type = lib.types.nullOr lib.types.singleLineStr;
        default = null;
        example = "/run/secrets/secretFile";
        description = ''
          Path to file to load secrets from. All secrets should be written as environment variables (in NAME=VALUE declarations, one per line). The content of the file most likely should look something like this (assuming that you used the !ENV expression in the settings section for session_secret_key and smtp password):
          ```
          JWT_SECRET_KEY=<your jwt secret key>
          SMTP_PASSWORD=<password of your user at your smtp server>
          ```
          This file should be accessable by the user [user](${cfg_str}.user) and by this user only!
        '';
      };
    };
  };

  config =
    let
      fileWithoutEnvs = yamlFormat.generate "project-W-backend-untreaded-config.yaml" cfg.settings;
      configFile = pkgs.writeTextDir "config.yml" (
        builtins.replaceStrings [ "'!ENV " ] [ "!ENV '" ] (builtins.readFile fileWithoutEnvs)
      );
    in
    lib.mkIf cfg.enable {
      #setup systemd service
      systemd = {
        services.project-W-backend = {
          description = "Project-W backend server";
          after = [ "network.target" ];
          wantedBy = [ "multi-user.target" ];
          serviceConfig = {
            User = cfg.user;
            Group = cfg.group;
            UMask = "0077";
            ExecStart = lib.escapeShellArgs [
              "${lib.getExe cfg.package}"
              "--custom_config_path"
              configFile
              "--root_static_files"
              cfg.frontend_package
            ];
            PrivateTmp = true;
            EnvironmentFile = lib.mkIf (cfg.envFile != null) cfg.envFile;
          };
        };
      };

      #setup user/group under which systemd service is run
      users.users = lib.mkIf (cfg.user == "project-W") {
        project-W = {
          inherit (cfg) group;
          isSystemUser = true;
        };
      };
      users.groups = lib.mkIf (cfg.group == "project-W") { project-W = { }; };
    };
}
