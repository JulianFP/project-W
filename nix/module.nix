inputs: {config, lib, pkgs, ...}: 
let
  inherit (lib)
    mdDoc
    mkIf
    mkOption
    mkEnableOption
    mkDefault
    types
    getExe
    escapeShellArgs
    ;
  inherit (pkgs.stdenv.hostPlatform) system;
  cfg = config.services.project-W-backend;
  cfg_str = "services.project-W-backend";
in {
  options = {
    services.project-W-backend = {
      enable = mkEnableOption (mdDoc "Backend of Project-W");
      package = mkOption {
        type = types.package;
        default = inputs.self.packages.${system}.project-W;
        description = mdDoc ''
          Project-W python package to use.
        '';
      };
      user = mkOption {
        type = types.singleLineStr;
        default = "project-W";
        description = mdDoc ''
          User account under which project-W runs.
        '';
      };
      group = mkOption {
        type = types.singleLineStr;
        default = "project-W";
        description = mdDoc ''
          User group under which project-W runs. This is for the service and flask stuff, the socket for communication between this service and nginx will always be set to [services.nginx.group](config.services.nginx.group) regardless.
        '';
      };
      hostName = mkOption {
        type = types.singleLineStr;
        description = mdDoc ''
          FQDN for the project-W backend instance.
        '';
      };
      settings = {
        clientURL = mkOption {
          type = types.strMatching "^(http|https):\/\/(([a-zA-Z0-9\-]+\.)+[a-zA-Z0-9\-]+|localhost)(:[0-9]+)?((\/[a-zA-Z0-9\-]+)+)?(\/#)?$";
          example = "https://example.com/#";
          description = mdDoc ''
            URL under which the client is hosted (including http/https, port, shouldn't end with /). If your client uses hash routing (like our official frontend), please add '/#' to the end of the URL.
          '';
        };
        databasePath = mkOption {
          type = types.singleLineStr;
          default = "/var/lib/project-W-backend/database";
          description = mdDoc ''
            Directory containing the servers database file.
          '';
        };
        loginSecurity = {
          sessionSecretKey = mkOption {
            type = types.singleLineStr;
            default = "!ENV \${JWT_SECRET_KEY}";
            description = mdDoc ''
              Secret key used to generate JWT Tokens. Warning: This will be public in the /nix/store! For production systems please use [envFile](${cfg_str}.envFile) combined with a secret management tool like sops-nix instead!!!
            '';
          };
          sessionExpirationTimeMinutes = mkOption {
            type = types.ints.between 5 2147483647;
            default = 60;
            description = mdDoc ''
              Duration for which JWT Tokens stay valid in minutes. After this duration users will have to relogin again
            '';
          };
          allowedEmailDomains = mkOption {
            type = types.listOf (types.strMatching "^([a-zA-Z0-9\-]+\.)+[a-zA-Z0-9\-]+$");
            default = [ ];
            example = [ "uni-heidelberg.de" "stud.uni-heidelberg.de" ];
            description = mdDoc ''
              Domains that are allowed to be used for the email address of the project-W user account (e.g. during signup). If not empty, emails with different domains can't be used by the users. If empty, all emails will be accepted.
            '';
          };
          disableSignup = mkOption {
            type = types.bool;
            default = false;
            description = mdDoc ''
              Whether signup of new project-W accounts should be possible. If enabled, only users that already have an account will be able to use the service.
            '';
          };
        };
        smtpServer = {
          domain = mkOption {
            type = types.strMatching "^([a-zA-Z0-9\-]+\.)+[a-zA-Z0-9\-]+|localhost$";
            example = "smtp.gmail.com";
            description = mdDoc ''
              Domain of the smtp server you want to use.
            '';
          };
          port = mkOption {
            type = types.port;
            example = 587;
            description = mdDoc ''
              Port of the smtp server you want to use. This might depend on [smtpServer.secure](${cfg_str}.settings.smtpServer.secure)
            '';
          };
          secure = mkOption {
            type = types.enum [ "ssl" "starttls" "unencrypted" ];
            example = "starttls";
            description = mdDoc ''
              Whether the connection to the smtp server should be encrypted and if yes which protocol to use. Remember to set [smtpServer.port](${cfg_str}.settings.smtpServer.port) accordingly.
            '';
          };
          senderEmail = mkOption {
            type = types.singleLineStr;
            example = "example@gmail.com";
            description = mdDoc ''
              Email address from which emails will be sent to the users. Usually also used as [smtpServer.username](${cfg_str}.settings.smtpServer.username).
            '';
          };
          username = mkOption {
            type = types.singleLineStr;
            example = "example@gmail.com";
            description = mdDoc ''
              Used to authenticate at the smtp server. Usually the same as [smtpServer.senderEmail](${cfg_str}.settings.smtpServer.senderEmail).
            '';
          };
          password = mkOption {
            type = types.singleLineStr;
            default = "!ENV \${SMTP_PASSWORD}";
            description = mdDoc ''
              Used to authenticate to the smtp server. Warning: This will be public in the /nix/store! For production systems please use [envFile](${cfg_str}.envFile) combined with a secret management tool like sops-nix instead!!!
            '';
          };
        };
      };
      envFile = mkOption {
        type = types.nullOr types.singleLineStr;
        default = null;
        example = "/run/secrets/secretFile";
        description = mdDoc ''
          Path to file to load secrets from. All secrets should be written as environment variables (in NAME=VALUE declerations, one per line). Per default, JWT_SECRET_KEY sets the secret key, and SMTP_PASSWORD sets the password for the smtp server. The content of the file most likely should look like this:
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
    socketDir = "/var/run/project-W";
    socketName = "project-W-gunicorn_nginx-socket.sock";
    configFile = pkgs.writeTextDir "config.yml" (builtins.toJSON cfg.settings);
    pythonPackage = (pkgs.python3.withPackages (ps: [
      cfg.package
      ps.gunicorn
    ]));
    envExists = (attrSet:
      let 
        v = builtins.attrValues attrSet; 
        boolFunc = (element:
          if (builtins.isAttrs element) then (envExists element)
          else if (builtins.isString element && (builtins.substring 0 5 element) == "!ENV ") then true
          else false
        );
        iterateV = (i:
          if (i >= (builtins.length v)) then false
          else if (boolFunc (builtins.elemAt v i)) then true 
          else iterateV (i+1)
        );
      in
      iterateV 0
    );
  in mkIf cfg.enable {
    assertions = [
      {
        assertion = !(envExists cfg.settings) || cfg.envFile != null;
        message = "The ${cfg_str}.envFile option can't be null if some of your options start with '!ENV '. Per default secrets like ${cfg_str}.settings.loginSecurity.sessionSecretKey and ${cfg_str}.settings.smtpServer.password have to be set in envFile.";
      }
    ];
    systemd = {
      #create directories for persistent stuff
      tmpfiles.settings.project-W-backend-dirs = {
        "${cfg.settings.databasePath}"."d" = {
          mode = "700";
          inherit (cfg) user group;
        };
        "${socketDir}"."d" = {
          mode = "770";
          inherit (cfg) user;
          group = config.services.nginx.group;
        };
      };

      #setup systemd service for gunicorn
      services.project-W-backend = {
        description = "Project-W backend server";
        after = [ "network-online.target" ];
        wants = [ "network-online.target" ];
        wantedBy = [ "multi-user.target" ];
        serviceConfig = {
          Type = "simple";
          User = cfg.user;
          Group = cfg.group;
          UMask = "0077";
          ExecStart = escapeShellArgs [
            "${getExe pythonPackage}"
            "-m" "gunicorn"
            "--bind" "unix:${socketDir}/${socketName}"
            "project_W:create_app('${configFile}')"
          ];
          Restart = "on-failure";
          EnvironmentFile = mkIf (cfg.envFile != null) cfg.envFile;
        };
      };
    };

    #setup user/group under which systemd service is run
    users.users = mkIf (cfg.user == "project-W") {
      project-W = {
        inherit (cfg) group;
        isSystemUser = true;
      };
    };
    users.groups = mkIf (cfg.group == "project-W") {
      project-W = {};
    };

    #setup nginx to serve requests
    services.nginx = {
      enable = mkDefault true;
      recommendedOptimisation = mkDefault true;
      recommendedProxySettings = mkDefault true;

      virtualHosts.${cfg.hostName}.locations."/api/".proxyPass = "http://unix:${socketDir}/${socketName}";
    };
  };
}
