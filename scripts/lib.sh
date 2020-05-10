#!/usr/bin/env bash

set -eu

memcached_container="servicelib-memcached"
redis_container="servicelib-redis"

function create_venv() {
  env="$1"
  tox --recreate --notest -e "$env"
}

function stop_aux_services() {
  docker rm -vf "$memcached_container" > /dev/null 2>&1 || true
  docker rm -vf "$redis_container" > /dev/null 2>&1 || true
}

function start_aux_services() {
  stop_aux_services

  docker run --rm --detach --publish 6379:6379 --name "$redis_container" redis > /dev/null
  docker run --rm --detach --publish 11211:11211 --name "$memcached_container" memcached > /dev/null
}
