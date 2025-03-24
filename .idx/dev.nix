# To learn more about how to use Nix to configure your environment
# see: https://developers.google.com/idx/guides/customize-idx-env
{ pkgs, ... }: {
  # Which nixpkgs channel to use.
  channel = "stable-24.05"; # or "unstable"

  # Use https://search.nixos.org/packages to find packages
  packages = [
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.python311Packages.virtualenv
    # pkgs.python311Packages.gunicorn
    pkgs.python311Packages.django
    pkgs.python311Packages.django-environ
    # pkgs.postgresql # Optional: If using PostgreSQL with Django
  ];

  # Sets environment variables in the workspace
  env = {
    DJANGO_ENV = "development";
  };

  idx = {
    # Search for the extensions you want on https://open-vsx.org/ and use "publisher.id"
    extensions = [
      "ms-python.python"
      "batisteo.vscode-django"
    ];

    # Enable previews
    previews = {
      enable = true;
      previews = {
        web = {
          # Run Django's development server
          command = ["python" "manage.py" "runserver" "0.0.0.0:$PORT"];
          manager = "web";
          env = {
            PORT = "$PORT";
          };
        };
      };
    };

    # Workspace lifecycle hooks
    workspace = {
      # Runs when a workspace is first created
      onCreate = {
        setup-venv = ''
          python -m venv venv
          source venv/bin/activate
          pip install -r requirements.txt
        '';
      };
      # Runs when the workspace is (re)started
      onStart = {
        activate-venv = "source venv/bin/activate";
      };
    };
  };
}
