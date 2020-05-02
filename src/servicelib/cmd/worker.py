# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import absolute_import, unicode_literals

import os
import sys

import psutil

from servicelib import config, logutils
from servicelib.compat import Path
from servicelib.config import cmdline
from servicelib.config.client import env_var


def main():
    logutils.configure_logging()

    cmdline_config = cmdline.parse_args(
        "worker.autoreload",
        "worker.hostname",
        "worker.load_workers",
        "worker.num_processes",
        "worker.num_threads",
        "worker.port",
        "worker.services_dir",
    )
    for k, v in cmdline_config.items():
        os.environ[env_var(k)] = str(v)

    cmd = ["uwsgi", "--req-logger", "file:/dev/null"]

    autoreload = int(config.get("worker.autoreload", "0"))
    if autoreload > 0:
        cmd.extend(["--py-autoreload", "{}".format(autoreload)])  # pragma: no cover

    serve_results = config.get("worker.serve_results", default=None)
    if serve_results is not None:
        for dname in serve_results.split(":"):
            cmd.extend(["--static-map", "{}={}".format(dname, dname)])

    swagger_yaml = Path(
        config.get("worker.services_dir", default="/code/services"), "swagger.yaml"
    )
    if swagger_yaml.exists():
        cmd.extend(["--static-map", "/services/swagger.yaml={}".format(swagger_yaml)])

    swagger_ui = Path(
        config.get("worker.swagger_ui_path", default="/usr/share/nginx/html")
    )
    if swagger_yaml.exists():
        cmd.extend(["--static-map", "/docs={}".format(swagger_ui)])
        cmd.extend(["--static-index", "index.html"])

    static_assets = config.get("worker.static_map", default=None)
    if static_assets is not None:
        cmd.extend(["--static-map", static_assets])

    cmd.append(
        config.get(
            "worker.uwsgi_config_file",
            default=str(Path(logutils.__file__, "..", "uwsgi.ini").resolve()),
        )
    )

    os.environ.setdefault(
        env_var("worker.num_processes"),
        config.get("worker.num_processes", str(psutil.cpu_count())),
    )
    os.environ.setdefault(
        env_var("worker.num_threads"), str(config.get("worker.num_threads", 1))
    )
    os.environ.setdefault(env_var("worker.port"), str(config.get("worker.port", 8000)))

    log = logutils.get_logger("servicelib-worker")
    log.info("Environment: %s", os.environ)
    log.info("Running: %s", " ".join(cmd))

    # If we're running under `pytest-cov`, call `pytest_cov.embed.cleanup()`
    # before exec of uWSGI, so that we do not lose coverage info for this
    # Python module.
    if os.environ.get("COV_CORE_DATAFILE"):
        from pytest_cov.embed import cleanup

        cleanup()

    os.execlp(cmd[0], *cmd[0:])


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
