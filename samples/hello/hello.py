# Copyright (c) ECMWF 2020.

from __future__ import absolute_import, unicode_literals


def execute(context, name):
    return "Hello, {}!".format(name)


def main():
    from servicelib import service

    service.start_service()
