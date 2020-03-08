# Copyright (C) 2009 ECMWF

"""Server-side support and implementation code for the servicelib framework.

Execution environment code.

"""

from __future__ import absolute_import, print_function, unicode_literals

import os
import pprint
import subprocess

# import signal
# import sys

# import psutil

from servicelib.context import Context


__all__ = [
    "ProcessRunner",
]


# CATCH = (signal.SIGINT, signal.SIGTERM, signal.SIGQUIT)


class ProcessContext(Context):
    def __init__(self, name, metadata=None):
        super(ProcessContext, self).__init__(name, metadata)

    def set_start_stop(self, t1, t2):
        self.metadata.set_start_stop(t1, t2)


class ProcessRunner(object):
    def __init__(self, context, proc):
        self.context = context
        self.proc = proc
        self.log = context.log

    def run(self, output=None, info=None):
        cmdline, env = (self.proc.cmdline, self.proc.env)
        if env is None:
            env = dict(os.environ)

        self.proc.context = ProcessContext(os.path.basename(cmdline[0]))

        cmdline = [str(x) for x in cmdline]
        msg = "Calling '{}'".format(" ".join(cmdline))
        self.log.debug(msg)
        if callable(output):
            output(msg)

        cmdline_pretty = " ".join(cmdline)
        self.log.debug("Environment: %s", pprint.pformat(env))
        with self.proc.context.timer("run"):
            try:
                p = subprocess.Popen(
                    cmdline, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env
                )
            except Exception as e:
                raise Exception("Failed to start '{}': {}".format(cmdline_pretty, e))

            self.log.debug("PID of '%s': %s", cmdline_pretty, p.pid)

            # In the Celery days we used to install here a signal handler for
            # SIGINT, SIGQUIT and SIGTERM which did the following:
            #
            # * Send the received signal to the process we just spawned, and to
            #   all of its descendents.
            # * Call the saved signal handler we overrode.
            #
            # The aim of that was to avoid having orphan process (MARS clients
            # and `magjson` instances, for instance) when the Celery workers
            # were restarted.
            #
            # If I understand correctly the way uWSGI handles signals:
            #
            #   https://uwsgi-docs.readthedocs.io/en/latest/Management.html
            #
            # ... uWSGI takes care of that for us, so we do not need to do that.

            self.proc.process_started()
            if callable(info):
                info(cmdline, env, p.pid)

            while True:
                out = p.stdout.readline()
                if len(out) == 0:
                    break
                if callable(output):
                    output(out)
                self.proc.stdout_data(out)

            rc = p.wait()

            # In the Celery days we restored here the original signal handlers.

            result = self.proc.process_ended(rc, 0)

        timers = self.proc.timers()
        if timers:
            self.proc.context.metadata.update_timers(timers)

        msg = "Process '{}' finished".format(cmdline_pretty)
        if callable(output):
            output(msg)

        self.context.update_metadata(self.proc.context.metadata)
        self.log.debug(msg)
        return result
