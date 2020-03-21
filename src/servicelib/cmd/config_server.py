# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import absolute_import, unicode_literals

import argparse
import os
import sys

from servicelib.compat import env_var


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--log-file",
        metavar="PATH",
        help="path to the log file (default: %(default)s)",
        default=None,
    )
    p.add_argument(
        "--pid-file",
        metavar="PATH",
        help="path to the PID file (default: %(default)s)",
        default=None,
    )
    p.add_argument(
        "--port",
        metavar="PORT",
        type=int,
        help="listening port (default: %(default)d)",
        default=9999,
    )
    p.add_argument(
        "--read-only", action="store_true", help="disable updates", default=False
    )
    p.add_argument(
        "--config-file",
        metavar="PATH",
        help="path to the config file (default: %(default)s)",
        default="servicelib.yaml",
    )

    args = p.parse_args()

    cmd = [
        "uwsgi",
        "--die-on-term",
        "--enable-threads",
        "--http-socket",
        ":{}".format(args.port),
        "--manage-script-name",
        "--master",
        "--module",
        "servicelib.config.wsgi",
        "--need-app",
        "--processes",
        "1",
        "--req-logger",
        "file:/dev/null",
        "--threads",
        "1",
    ]

    if args.pid_file is not None:
        cmd.extend(
            [
                "--safe-pidfile",
                args.pid_file,
                "--daemonize",
                args.log_file is not None and args.log_file or "/dev/null",
            ]
        )

    os.environ.setdefault(
        *env_var("SERVICELIB_CONFIG_FILE", os.path.abspath(args.config_file))
    )
    os.environ.setdefault(
        *env_var(
            "SERVICELIB_CONFIG_SERVER_READ_ONLY", "true" if args.read_only else "false"
        )
    )

    # If we're running under `pytest-cov`, call `pytest_cov.embed.cleanup()`
    # before exec of uWSGI, so that we do not lose coverage info for this
    # Python module.
    if os.environ.get("COV_CORE_DATAFILE"):
        from pytest_cov.embed import cleanup

        cleanup()

    os.execlp(cmd[0], *cmd[0:])


if __name__ == "__main__":
    sys.exit(main())
