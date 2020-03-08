# Design

## Service API

Services accept JSON-encoded requests, and produce JSON-formatted responses.


### Requests

Requests are sent using HTTP `POST` requests. The HTTP request body is a JSON
array (possibly empty), which represents the arguments to the service.

Requests may encode optional metadata in the following HTTP request headers:

* `x-servicelib-uid`: String with the identity of the user calling the service.
* `x-servicelib-tracker`: String to correlate several service calls together.
* `x-servicelib-cache`: Boolean which, when set to `true`, lets service
  implementations return previously cached responses to the same request.

The path component of the URL endpoint of a given service is
`/services/<service-name>`.


### Responses

The body of the HTTP response is a JSON-encoded object. Its structure depends on
the HTTP status code of the reponse.

Requests which have beem successfully processed have an HTTP status code of
`200`. The response body is an arbitrary JSON value.

Any other HTTP status code represents a processing error. In this case the
reponse body is a JSON object with the following fields:

* `error` (mandatory): A string representation of the error.
* `traceback` (optional): A free-form field representing a stack trace of where
  the error happened.

The following HTTP status codes for errors are suggested:

* 401: The service did not process the request because the identity of the
  caller could not be established.
* 403: The service did not process the request because the caller is not
  allowed to call the service.
* 404: The service is not supported.
* 419: The request was malformed, and could not be understood by the service.
  Further calls to this service with the same request will fail.
* 500: A processing error happened. Further calls to this service may succeed.

When the results of a request are large, they may be returned off-line, instead
of in the HTTP reponse body. In this case the HTTP response body is a JSON
object with the following fields:

* `location` (mandatory): A URL where the result may be accessed.
* `contentType` (optional): The content type of the bytes behind the URL.
* `contentLength` (optional): The length of the bytes behind the URL.


## Service instances and workers

Services are packaged in container images. Each container image may implement
more than one service. A worker is a container instance which implements one
or more services.

The host environment creates container instances from those container images.
The processes within container instances run under non-root UIDs. Their
root file system is mounted in read-only mode.


### HTTP endpoints

Container instances accept HTTP requests. They listen on the TCP port specified
by the `SERVICELIB_WORKER_PORT` environment variable. That port number may be 0,
in which case the service implementation will choose an arbitrary port (this is
required for compatibility with the non-containerised version of eccharts
services).

Container instances accept HTTP `GET` requests to the path `/health`, and reply
with an HTTP 200 status code to signal that they are ready to accept service
requests. If there is no reponse, or if the HTTP status code is not 200, the
service implementation is not ready to accept requests.

Container instances accept HTTP `GET` requests to the path `/config`, and reply
with a JSON object object with the following fields:

* `services`: An array of strings with the names of the services they implement.
* `port`: The TCP port number in which they listen for HTTP requests. If they
  have chosen an arbitrary port, its value will be returned here. This `port`
  field is required for compatibility with the non-containerised version of
  eccharts services).

For each service they implement, container instances accept HTTP `POST` requests
to the path `/service/<service-name>`, as described above in "Service API".


### Storage

Processes in the container instances may write to several directories.

For temporary files, the usual `/tmp` directory is available. Since `/tmp` might
mount a memory-backed file system, it should not be used for creating large
files.

For returning large results off-line, one or more directories may also be
available. Their locations are specified by the environment variable
`ECMWF_SERVICELIB_DOWNLOAD_DIRS`. The value of this variable is a
colon-separated list of directory paths. In order to return a large
result off-line, services must do the following:

* Randomly choose a directory from those specified in the environment variable
  `ECMWF_SERVICELIB_DOWNLOAD_DIRS`.
* Write the results of the request to a world-readable file under that
  directory.
* Generate a URL for that file, by concatenating the value of the environment
  variable `ECMWF_SERVICELIB_DOWNLOAD_URL_PREFIX` and the absolute path to the
  results file. If the environment variable
  `ECMWF_SERVICELIB_DOWNLOAD_URL_PREFIX` contains the sequence `$(FOO)`,
  services will replace that sequence with the value of the environment variable
  `_ECMWF_SERVICELIB_FOO`.
* Return that URL in a JSON object as described above in "Service API".

If the environment variable `ECMWF_SERVICELIB_DOWNLOAD_DIRS` is not set, then no
directories are available to create result files which may be returned off-line.
Ini this case, services would still be able to return large results off-line by
writing to some external object storage service, for instance.


## Host environments

Services may run in any of the following environments:

* Metview instances running on Linux environments (and possibly on macOS and
  Windows environments, too).
* Server-side Kubernetes applications, like the future ecCharts.
* Server-side VM-based applications, like the current ecCharts or the CDS.

Services may also run in the current, non-containerised ecCharts deployment,
once the migration from Celery to HTTP has been finished.


### Metview

In order to instantiate the services packaged in a given container image, the
Metview main program first chooses an available TCP port in the local system. It
also creates two directories on the local disk: One for temporary usage, and
another one for letting the container return large results off-line. It also
chooses some unique name for this container instance (unique within the set of
all container names running on the host).

Metview then instantiates the container image, doing something like this:

```
$ docker run \
    --detach \
    --env ECMWF_SERVICELIB_DOWNLOAD_DIRS='["/data/scratch"]' \
    --env ECMWF_SERVICELIB_DOWNLOAD_URL_PREFIX= \
    --env ECMWF_SERVICELIB_SERVICE_PORT=8080 \
    --name <some-name> \
    --publish <some-port>:127.0.0.1:8080 \
    --read-only \
    --user $UID \
    --volume <results-dir>:/data/scratch \
    --volume <tmp-dir>:/tmp \
    <image-name>
```

Once the container is up, Metview calls the config endpoint
`http://127.0.0.1:<some-port>/config`, in order to determine the endpoints of
the services implemented in this container instamce. This lets Metview register
internally each service (eg. `foo`), and map it to its URL endpoint (eg.
`http://127.0.0.1:8080/services/foo`).

When Metview is about to exit, it first kills all containers it has spawned, and
cleans up their temporary directories.


### Kubernetes

Services are deployed in
[pods](https://kubernetes.io/docs/concepts/workloads/pods/pod-overview/),
controlled by [deployment
controller](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/).

A [Kubernetes
service](https://kubernetes.io/docs/concepts/services-networking/service/) takes
care of load-balancing requests among them. If the name of the Kubernetes
service is `<some-name>`, and the pods implement services `foo` and `bar`, then
the URL endpoints of those services will be, respectively,
`http://<some-name>:8080/services/foo` and
`http://<some-name>:8080/services/bar`.

Those URLs will be valid within the
Kubernetes cluster, and may be exposed outside of the Kubernetes cluster with
[Kubernetes ingress
definitions](https://kubernetes.io/docs/concepts/services-networking/ingress/).

Pod definitions include several containers. One runs the service container
image, and another one runs an Nginx instance to serve the large result files
off-line (which are written into a volume shared by both containers).

Off-line results volumes may also be shared among all pods, if the under;ying
Kubernetes cluster supports [persistent
volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/) with
`ReadWriteMany` [access
mode](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#access-modes).
In this case, if the name of the Kubernetes service in front of the pods is
`<some-name>`, those result files will be accessible under the URL prefix
`http://<some-name>:8081`. This setup may improve caching of results.

A pod specification might look like this:


```
apiVersion: v1
kind: Pod
# [..]
spec:
  containers:
    - name: services
      image: <image-name>
      env:
        - name: ECMWF_SERVICELIB_DOWNLOAD_DIRS
          value: '["/data/scratch"]'
        - name: ECMWF_SERVICELIB_DOWNLOAD_URL_PREFIX
          value: http://$(DOWNLOAD_HOSTNAME):8081
        - name: _ECMWF_DOWNLOAD_HOSTNAME
          valueFrom:
            fieldRef:
              fieldPath: status.podIP
        - name: ECMWF_SERVICELIB_SERVICE_PORT
          value: "8080"
      ports:
        - name: service
          containerPort: 8080
      volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: download-dirs
          mountPath: /data/scratch
      readinessProbe:
        httpGet:
          path: /health
          port: 8080
      securityContext:
        readOnlyRootFilesystem: true

    - name: download
      image: nginx
      ports:
        - name: http
          containerPort: 8081
      volumeMounts:
        - name: download-dirs
          mountPath: /data/scratch
  volumes:
    - name: tmp
      [..]
    - name: download-dirs
      [..]
```


### VM-based environments
