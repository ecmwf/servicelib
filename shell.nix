let
  sources = import ./nix/sources.nix;
  pkgs = import sources.nixpkgs { };
in
pkgs.mkShell {
  buildInputs = with pkgs; [
    # Needed to install uWSGI.
    expat
    libintl
    libxml2
    ncurses
    pcre

    # Install Python 2.7 runtime for tests.
    python27

    # Install Python 3.8 runtime for tests and build tools.
    (python38.withPackages
      (ps: with ps ; [
        flit
        tox
      ]))


    # Niv (https://github.com/nmattia/niv), to keep dependencies up-to-date.
    #
    # (`niv` on macOS M1 cannot be installed from 21.05)
    # niv

    # Keep this line if you use bash.
    bashInteractive
  ] ++ lib.optionals stdenv.isDarwin [ darwin.IOKit ];
}
