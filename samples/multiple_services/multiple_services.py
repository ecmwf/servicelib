# Copyright (c) ECMWF 2020.

from __future__ import absolute_import, unicode_literals


def hola(context, name):
    return "Homa, {}!".format(name)


def bonjour(context, name):
    return "Bonjour, {}!".format(name)


def main():
    from servicelib import service

    service.start_services(
        {"name": "hola", "execute": hola}, {"name": "bonjour", "execute": bonjour},
    )
