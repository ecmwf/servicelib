# Copyright (c) ECMWF 2020.

from __future__ import absolute_import, unicode_literals


def execute(context):
    return set(["This cannot be encoded in JSON"])


def main():
    from servicelib import service

    service.start_service()
