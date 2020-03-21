# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from __future__ import absolute_import, print_function, unicode_literals

import argparse
import difflib
import json
import sys


from servicelib import logutils
from servicelib.config import client


def _set(client, args):
    key, value = args.key, args.value
    try:
        value = json.loads(value)
    except Exception:
        print("Invalid JSON: <{}>".format(value), file=sys.stderr)
        return 1
    client.set(key, value)


def _get(client, args):
    try:
        print(json.dumps(client.get(args.key, exact=True)))
    except Exception as exc:
        print(exc, file=sys.stderr)
        return 1


def _delete(client, args):
    try:
        client.delete(args.key)
    except KeyError:
        print("{}: Not found".format(args.key), file=sys.stderr)
        return 1


def _dump(client, args):
    print(json.dumps(client.dump(), indent=4))


def _diff(_, args):
    source = client.instance(url=args.src).dump()
    dest = client.instance(url=args.dest).dump()

    def diff0(src, src_base, dst, dst_base):
        src_keys = set(src)
        dst_keys = set(dst)

        def name(bits):
            return ".".join(bits)

        for k in sorted(src_keys.difference(dst_keys)):
            print("Only in {}: {}".format(args.src, name(src_base + [k])))

        for k in sorted(src_keys.intersection(dst_keys)):
            src_val, dst_val = src[k], dst[k]
            if src_val == dst_val:
                continue

            if isinstance(src_val, dict):
                diff0(src_val, src_base + [k], dst_val, dst_base + [k])
            else:
                src_val = [
                    line + "\n" for line in json.dumps(src_val, indent=1).split("\n")
                ]
                dst_val = [
                    line + "\n" for line in json.dumps(dst_val, indent=1).split("\n")
                ]
                delta = difflib.unified_diff(
                    src_val, dst_val, name(src_base + [k]), name(dst_base + [k])
                )
                print("".join(delta))

        for k in sorted(dst_keys.difference(src_keys)):
            print("Only in {}: {}".format(args.dest, name(dst_base + [k])))

    diff0(source, [], dest, [])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config-url", metavar="URL", help="URL of the config server", default=None
    )
    parser.add_argument(
        "--verbose", action="store_true", help="verbose operation", default=False
    )
    subparsers = parser.add_subparsers(help="commands")

    get_p = subparsers.add_parser("get", help="get the value of a config key")
    get_p.add_argument("key", metavar="<key>")
    get_p.set_defaults(func=_get)

    set_p = subparsers.add_parser("set", help="set the value of a config key")
    set_p.add_argument("key", metavar="<key>")
    set_p.add_argument("value", metavar="<value>")
    set_p.set_defaults(func=_set)

    del_p = subparsers.add_parser(
        "delete", help="remove a setting value from the config source"
    )
    del_p.add_argument("key", metavar="<key>")
    del_p.set_defaults(func=_delete)

    dump_p = subparsers.add_parser("dump", help="Dump config in JSON format to stdout")
    dump_p.set_defaults(func=_dump)

    diff_p = subparsers.add_parser("diff", help="compare config from two sources")
    diff_p.add_argument("src", metavar="<source url>")
    diff_p.add_argument("dest", metavar="<dest url>")
    diff_p.set_defaults(func=_diff)

    args = parser.parse_args()

    logutils.configure_logging(level=args.verbose and "DEBUG" or "WARN")

    c = client.instance(url=args.config_url)
    return args.func(c, args)


if __name__ == "__main__":
    sys.exit(main())
