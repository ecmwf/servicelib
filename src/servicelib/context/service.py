# Copyright (C) 2009 ECMWF

"""Server-side support and implementation code for the servicelib framework.

Execution environment code.

"""

from __future__ import absolute_import, unicode_literals

import os

from servicelib import logutils, results, scratch
from servicelib.context import Context
from servicelib.context.process import ProcessRunner


__all__ = [
    "ServiceContext",
]


class ServiceContext(Context):

    """Execution context for a service call."""

    def __init__(self, name, home, metadata, request):
        super(ServiceContext, self).__init__(name, metadata)
        self._name = name
        self.home = home
        self.request = request
        self._temp_files = set()
        self._results = results.instance()
        self._scratch = scratch.instance()
        self.log = logutils.get_logger(name).bind(user=self.uid, tracker=self.tracker)
        for k, v in self.request.kwargs.items():
            self.annotate(k, v)

    def rename(self, name):
        self._name = name

    @property
    def uid(self):
        return self.request.uid

    @property
    def tracker(self):
        return self.request.tracker

    def service_home(self, fname=""):
        dname = self.home
        return os.path.abspath(os.path.join(dname, fname))

    def spawn_process(self, proc):
        """Spawns a process.

        `proc` must be an instance of `servicelib.process.Process`.

        """

        ofunc = None
        ifunc = None

        # def send_info(ref, cmdline, env, childpid):
        #     info = {
        #         "host": HOSTNAME.split(".")[0],
        #         "pid": os.getpid(),
        #         "cmdline": cmdline,
        #         "env": env,
        #         "childpid": childpid,
        #     }
        #     self.log.info("Process spawned: %s", cmdline, taskid=ref, childpid=childpid)
        #     batch.batch_info(ref, info)

        # if "info" in self.request.kwargs:
        #     id = self.request.kwargs["info"]
        #     ifunc = lambda *args: send_info(id, *args)

        # if "output" in self.request.kwargs:
        #     id = self.request.kwargs["output"]
        #     ofunc = lambda line: batch.batch_log(id, line)

        p = ProcessRunner(self, proc)
        return p.run(output=ofunc, info=ifunc)

    def pre_execute_hook(self, broker, service, args, kwargs):
        for k, v in self.request.kwargs.items():
            kwargs.setdefault(k, v)

    def create_result(self, content_type):
        return self._results.create(content_type)

    def cleanup(self):
        for tmp in self._temp_files:
            try:
                os.unlink(tmp)
            except Exception as exc:
                self.log.exception("Cannot remove temp file %s: %s", tmp, exc)

    def create_temp_file(self):
        """Create a temporary file, which will be deleted when `cleanup()` is
        called.

        """
        ret = self._scratch.create_temp_file()
        self._temp_files.add(ret)
        return ret

    def get_data(self, result):
        with self.timer("getdata"):
            try:
                path = self._results.as_local_file(result)
            except NotImplementedError:
                pass
            else:
                if path is not None:
                    return path

            with self.timer("download"):
                return self._scratch.as_local_file(result)
