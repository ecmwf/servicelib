# Copyright (C) ECMWF 2015

from servicelib import errors


class CustomError(Exception):
    pass


def raise_service(context, exc_name, *exc_args):
    context.log.info("raise(%s, %s): Entering", exc_name, exc_args)

    if exc_name == "CustomError":
        exc = CustomError(*exc_args)
    elif exc_name == "IOError":
        try:
            open(exc_args[0])
        except IOError as io_exc:
            exc = io_exc
    elif exc_name == "BadRequest":
        exc = errors.BadRequest(*exc_args)
    elif exc_name == "RetryLater":
        exc = errors.RetryLater(*exc_args)
    else:
        try:
            exc_class = __builtins__[exc_name]
        except KeyError:
            context.log.exception("Unknown exception class '%s'", exc_name)
            raise Exception("<%s(%s)>" % (exc_name, exc_args))

        try:
            exc = exc_class(*exc_args)
        except Exception:
            context.log.exception("Cannot instantiate %s(%s)", exc_name, exc_args)
            exc = Exception("<%s(%s)>" % (exc_name, exc_args))

    context.log.info("Raising %s (type: %s)", exc, type(exc))
    raise exc


def raise_api_service(context, request):
    return raise_service(context, request["exc_name"], *request["exc_args"])


def main():
    from servicelib import service

    service.start_services(
        {"name": "raise", "execute": raise_service},
        {"name": "raise-api", "execute": raise_api_service},
    )


if __name__ == "__main__":
    main()
