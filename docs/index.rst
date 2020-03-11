============================================================
``servicelib``: Write services which talk JSON through HTTP.
============================================================

Create this directory structure::

    $ tree .
    .
    └── hello
        ├── hello.py
        └── __init__.py

    0 directories, 2 files
    $

Write this into ``hello/hello.py``:

.. code-block:: python

    def execute(context, arg):
        return "Hello, {}!".format(arg)

    def main():
        from servicelib.service import start_service
        start_service()

Start the worker process in a terminal with ``servicelib-worker``::

    $ env SERVICELIB_WORKER_SERVICES_DIR=$(pwd) servicelib-worker
    *** Starting uWSGI 2.0.18 (64bit) on [Tue Mar 10 14:53:06 2020] ***

            ... lots of output here ...

    2020-03-10 14:53:06,646 17490 MainProcess MainThread DEBUG servicelib.inventory Registering services in module: hello.hello
    2020-03-10 14:53:06,663 17490 MainProcess MainThread DEBUG servicelib.inventory Services: hello

Now you may call the service ``hello`` from another terminal::

    $ curl -v \
          -H 'Content-Type: application/json' \
          -d '["world"]' \
          http://127.0.0.1:8000/services/hello

    * TCP_NODELAY set
    * Connected to 127.0.0.1 (127.0.0.1) port 8000 (#0)
    > POST /services/hello HTTP/1.1
    > Content-Type: application/json
    >
    * upload completely sent off: 9 out of 9 bytes
    < HTTP/1.1 200 OK

        ... some headers here ...
    <
    * Connection #0 to host 127.0.0.1 left intact
    "Hello, world!"
    $


.. toctree::
   :maxdepth: 2
   :caption: Contents:


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
