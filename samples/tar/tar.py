# Copyright (c) ECMWF 2020.

from __future__ import absolute_import, unicode_literals

from servicelib import process


def tar_create(context, *paths):
    tar_file = context.create_result("application/x-tar")

    class p(process.Process):
        def __init__(self):
            super(p, self).__init__("tar", ["tar", "cvf", tar_file.path] + list(paths))

        def results(self):
            return tar_file

    return context.spawn_process(p())


def tar_list(context, tar_file):
    tar_file = context.get_data(tar_file)

    class p(process.Process):
        def __init__(self):
            super(p, self).__init__("tar", ["tar", "tvf", tar_file])

        def results(self):
            return self.output.decode("utf-8")

    return context.spawn_process(p())


def main():
    from servicelib import service

    service.start_services(
        {"name": "tar-create", "execute": tar_create,},
        {"name": "tar-list", "execute": tar_list,},
    )
