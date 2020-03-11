#!/usr/bin/env python

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


def main():
    logutils.configure_logging()

    cmd = ["uwsgi"]

    autoreload = int(config.get("worker_autoreload", "0"))
    if autoreload > 0:
        cmd.extend(["--py-autoreload", "{}".format(autoreload)])

    serve_results = config.get("worker_serve_results", default=None)
    if serve_results is not None:
        for dname in serve_results.split(":"):
            cmd.extend(["--static-map", "{}={}".format(dname, dname)])

    swagger_yaml = Path("/code/services/swagger.yaml")
    if swagger_yaml.exists():
        cmd.extend(["--static-map", "/docs/=/usr/share/nginx/html/"])
        cmd.extend(["--static-map", "/services/swagger.yaml={}".format(swagger_yaml)])

    cmd.append(
        config.get(
            "worker_uwsgi_config_file",
            default=str(Path(config.__file__, "..", "uwsgi.ini").resolve()),
        )
    )

    os.environ.setdefault(
        "SERVICELIB_WORKER_NUM_PROCESSES",
        config.get("worker_num_processes", str(psutil.cpu_count())),
    )
    os.environ.setdefault(
        "SERVICELIB_WORKER_NUM_THREADS", config.get("worker_num_threads", "1")
    )
    os.environ.setdefault("SERVICELIB_WORKER_PORT", config.get("worker_port", "8000"))

    log = logutils.get_logger("servicelib-worker")
    log.info("Running: %s", " ".join(cmd))
    os.execlp(cmd[0], *cmd[0:])


if __name__ == "__main__":
    sys.exit(main())
