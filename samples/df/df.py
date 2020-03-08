# Copyright (c) ECMWF 2020.

from __future__ import absolute_import, unicode_literals

from servicelib import process


def execute(context, *args):
    class p(process.Process):
        def __init__(self):
            super(p, self).__init__("df", ["df"] + list(args))

        def results(self):
            return self.output.decode("utf-8")

    return context.spawn_process(p())


def main():
    from servicelib import service

    service.start_service()
