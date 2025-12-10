{
  inputs,
  config,
  lib,
  pkgs,
  ...
}:
let
  inherit (pkgs.stdenv.hostPlatform) system;
  yamlFormat = pkgs.formats.yaml { };
  cfg = config.services.project-W.server;
  cfg_str = "services.project-W.server";
in
{
  options = {
    services.project-W.server = {
      enable = lib.mkEnableOption "Backend & Frontend of Project-W";
      package = lib.mkOption {
        type = lib.types.package;
        default = inputs.self.packages.${system}.project_W;
        description = ''
          Project-W backend package to use.
        '';
      };
      frontendPackage = lib.mkOption {
        type = lib.types.package;
        default = inputs.self.packages.${system}.project_W_frontend;
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
      enableLocalRedis = lib.mkOption {
        type = lib.types.bool;
        default = true;
        description = ''
          Whether to setup a local redis server for the Project-W backend. If this is set to false, then you need to provide some other redis server in the settings (i.e. running on a different machine).
        '';
      };
      enableLocalPostgres = lib.mkOption {
        type = lib.types.bool;
        default = true;
        description = ''
          Whether to setup a local PostgreSQL server for the Project-W backend. If this is set to false, then you need to provide some other PostgreSQL server in the settings (i.e. running on a different machine).
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
          SECRET_KEY=<your secret key>
          ADMIN_PASSWORD=<your admin user's password>
          SMTP_PASSWORD=<password of your user at your smtp server>
          ```
          This file should be accessible by the user [user](${cfg_str}.user) and by this user only!
        '';
      };
    };
  };

  config =
    let
      finalSettings =
        lib.optionalAttrs cfg.enableLocalRedis {
          redis_connection.unix_socket_path = "/var/run/redis-project-W/redis.sock";
        }
        // lib.optionalAttrs cfg.enableLocalPostgres {
          postgres_connection_string = "postgresql://project-w@%2Fvar%2Frun%2Fpostgresql/project-w";
        }
        // cfg.settings;
      fileWithoutEnvs = yamlFormat.generate "project-W-backend-untreaded-config.yaml" finalSettings;
      configFile = pkgs.writeTextDir "config.yml" (
        builtins.replaceStrings [ "'!ENV " ] [ "!ENV '" ] (builtins.readFile fileWithoutEnvs)
      );
    in
    lib.mkIf cfg.enable {
      #setup systemd service
      systemd.services = {
        project-W = {
          description = "Project-W backend server, also serving the frontend";
          wants =
            lib.optional cfg.enableLocalRedis "redis-project-w.service"
            ++ lib.optional cfg.enableLocalPostgres "postgresql.service";
          after = [
            "network.target"
          ]
          ++ lib.optional cfg.enableLocalRedis "redis-project-w.service"
          ++ lib.optional cfg.enableLocalPostgres "postgresql.service";
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
              cfg.frontendPackage
            ];
            PrivateTmp = true;
            EnvironmentFile = lib.mkIf (cfg.envFile != null) cfg.envFile;
          };
        };
        project-W_bg-tasks = {
          description = "Project-W periodic background tasks, running once a day";
          startAt = "*-*-* 00:00:00";
          wants =
            lib.optional cfg.enableLocalRedis "redis-project-w.service"
            ++ lib.optional cfg.enableLocalPostgres "postgresql.service";
          serviceConfig = {
            Type = "oneshot";
            User = cfg.user;
            Group = cfg.group;
            UMask = "0077";
            ExecStart = lib.escapeShellArgs [
              "${lib.getExe cfg.package}"
              "--custom_config_path"
              configFile
              "--run_periodic_tasks"
            ];
            PrivateTmp = true;
            EnvironmentFile = lib.mkIf (cfg.envFile != null) cfg.envFile;
          };
        };
      };

      services = {
        redis.servers."project-W" = lib.mkIf cfg.enableLocalRedis {
          enable = true;
          group = config.services.project-W.server.group;
        };
        postgresql = lib.mkIf cfg.enableLocalPostgres {
          enable = true;
          ensureDatabases = [ "project-w" ];
          ensureUsers = [
            {
              name = "project-w";
              ensureDBOwnership = true;
            }
          ];
          identMap = ''
            # ArbitraryMapName systemUser DBUser
              project-w_map postgres  postgres
              project-w_map ${cfg.user} project-w
          '';
          authentication = pkgs.lib.mkOverride 10 ''
            #type database  DBuser  auth-method optional_ident_map
            local sameuser  all     peer        map=project-w_map
          '';
        };
      };

      #setup user/group under which systemd service is run
      users.users = lib.mkIf (cfg.user == "project-W") {
        project-W = {
          inherit (cfg) group;
          isSystemUser = true;
        };
      };
      users.groups = lib.mkIf (cfg.group == "project-W") {
        project-W = { };
        redis-project-W = { };
      };
    };
}
