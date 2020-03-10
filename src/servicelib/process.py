# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import absolute_import, unicode_literals

from servicelib import logutils


# Maximum number of output from process (both `stdout` and `stderr`)
# to be kept.
#
# Set to zero for unlimited output.

DEFAULT_MAX_PROCESS_OUTPUT_SIZE = 10 * 1024


class Process(object):

    max_output_size = DEFAULT_MAX_PROCESS_OUTPUT_SIZE

    def __init__(self, name, cmdline=None, env=None):
        self.cmdline = [str(x) for x in cmdline]
        self.env = env
        self.name = name
        self.output = bytearray()

    def process_started(self):
        pass

    def stdout_data(self, data):
        if (
            self.max_output_size == 0
            or len(self.output) + len(data) <= self.max_output_size
        ):
            self.output.extend(data)

    def stderr_data(self, data):
        if (
            self.max_output_size == 0
            or len(self.output) + len(data) <= self.max_output_size
        ):
            self.output.extend(data)

    def process_ended(self, rc, signal):
        try:
            self.cleanup()
        except Exception:
            self.log.error("Error in `cleanup()`", exc_info=True)

        if rc or signal:
            cmdline = " ".join(self.cmdline)
            self.log.error("Failed: %s", cmdline)
            try:
                self.failed(rc, signal)
            except Exception:
                self.log.error("Error in `failed(%s, %s)`", rc, signal, exc_info=True)

            if signal:
                raise Exception(
                    "'{}' killed by signal {}:\n{}\n{}".format(
                        self.name, signal, cmdline, self.output
                    )
                )
            else:
                raise Exception(
                    "'{}' failed, return code {}:\n{}\n{}".format(
                        self.name, rc, cmdline, self.output
                    )
                )

        ret = self.results()
        return ret

    def results(self):
        raise NotImplementedError("Method `results() not implemented")

    def cleanup(self):
        pass

    def failed(self, rc, signal):
        pass

    def timers(self):
        pass

    @property
    def log(self):
        try:
            return self.context.log
        except AttributeError:
            return logutils.get_logger(__name__)
