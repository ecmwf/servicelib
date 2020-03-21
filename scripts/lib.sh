#!/usr/bin/env bash

set -e

memcached_container="servicelib-memcached"
redis_container="servicelib-redis"

function create_venv() {
  tox --recreate --notest -e py37
}

function stop_aux_services() {
  set -x
  docker rm -vf "$memcached_container" || true
  docker rm -vf "$redis_container" || true
  set +x
}

function start_aux_services() {
  stop_aux_services

  set -x
  docker run --rm --detach --publish 6379:6379 --name "$redis_container" redis
  docker run --rm --detach --publish 11211:11211 --name "$memcached_container" memcached
  set +x
}
