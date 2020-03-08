#!/usr/bin/env python

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

    serve_results = config.get("uwsgi_serve_results", default=None)
    if serve_results is not None:
        for dname in serve_results.split(":"):
            cmd.extend(["--static-map", "{}={}".format(dname, dname)])

    cmd.append(
        config.get(
            "uwsgi_config_file",
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
