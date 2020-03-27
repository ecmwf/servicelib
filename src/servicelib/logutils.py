# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Logging setup code."""

from __future__ import absolute_import, unicode_literals

import logging
import logging.config
import os

import structlog

from servicelib.compat import PY2


__all__ = [
    "configure_logging",
    "get_logger",
    "stdlib_log_config",
]


DEFAULT_FORMAT = (
    "%(asctime)s "
    "%(process)s "
    "%(processName)s "
    "%(threadName)s "
    "%(levelname)s "
    "%(name)s "
    "%(message)s"
)

LOG_LEVELS = set(("DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"))

LOG_TYPES = {"json", "text"}


def configure_logging(level="DEBUG", log_format=DEFAULT_FORMAT, log_type="text"):
    conf = stdlib_log_config(level=level, log_format=log_format, log_type=log_type)
    logging.config.dictConfig(conf)


def stdlib_log_config(level="DEBUG", log_format=DEFAULT_FORMAT, log_type="text"):
    if level not in LOG_LEVELS:
        raise ValueError("Invalid log level: {}".format(level))

    if log_type not in LOG_TYPES:
        raise ValueError("Invalid log type: {}".format(log_type))

    if PY2:
        unicode_processor = structlog.processors.UnicodeEncoder
    else:
        unicode_processor = structlog.processors.UnicodeDecoder

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            unicode_processor(),
            structlog.stdlib.render_to_log_kwargs,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    if log_type == "text":
        formatter = {
            "format": log_format,
        }
    else:
        formatter = {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": log_format,
        }

    conf = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"default": formatter,},
        "handlers": {
            "console": {
                "level": level,
                "class": "logging.StreamHandler",
                "formatter": "default",
            }
        },
        "loggers": {
            "": {"handlers": ["console"], "level": level, "propagate": True,},
            # "requests": {"handlers": ["console"], "level": "WARN", "propagate": False,},
        },
    }

    return conf


def get_logger(name=None):
    system = os.environ.get("SERVICELIB_LOG_SYSTEM_NAME")
    if system not in {None, ""}:
        logger = structlog.get_logger(name, system=system)
    else:
        logger = structlog.get_logger(name)
    return logger
