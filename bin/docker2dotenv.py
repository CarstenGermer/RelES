#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function

from collections import OrderedDict
from os import getenv
from os.path import abspath, isfile
import subprocess
import sys
from urlparse import urlparse, urlunparse

DOTENV_FILE = abspath('.env')

DATABASE_URL = 'DATABASE_URL'
ELASTICSEARCH_KEY = 'ELASTICSEARCH_HOST'

_DEFAULT_POSTGRES_USER = 'postgres'
_DEFAULT_POSTGRES_PASS = 'mysecretpassword'

def load_config(path):
    # type: (str) -> dict

    result = OrderedDict()
    if isfile(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('\'"')
                result[key] = value

    return result


def write_config(config, path):
    # type: (dict, str) -> None

    with open(path, 'wb+') as f:
        for key, value in config.items():
            f.write('{}={}\n'.format(key, value))


def get_docker_ip():
    # type: () -> str

    docker_host = getenv('DOCKER_HOST')
    if docker_host:
        url = urlparse(docker_host)
        return url.netloc.split(':')[0]

    docker_machine_name = getenv('DOCKER_MACHINE_NAME')
    if docker_machine_name:
        return subprocess.check_output(['docker-machine', 'ip', docker_machine_name]).strip()

    return '127.0.0.1'


def get_docker_compose_port(service_name, port):
    # type: (str, int) -> int

    try:
        port_info = subprocess.check_output(
            ['docker-compose', 'port', service_name, str(port)]
        )
    except subprocess.CalledProcessError:
        print(
            'ERROR: getting port for {} + {} (is docker-compose installed?)'.format(service_name, port),
            file=sys.stderr
        )
        sys.exit(1)

    return int(port_info.split(':')[1].strip())


def set_or_adjust_database(current, ip, port):
    # type: (str, str, int) -> str

    ip_port = ip_colon_port(ip, port)

    if current:
        url = urlparse(current)

        if url.username:
            username = url.username
        else:
            username = _DEFAULT_POSTGRES_USER

        if url.password:
            password = url.password
        else:
            password = _DEFAULT_POSTGRES_PASS

        new_netloc = '{}:{}@{}'.format(username, password, ip_port)

        result = urlunparse((
            url.scheme,
            new_netloc,
            url.path,
            url.params,
            url.query,
            url.fragment
        ))
    else:
        result = 'postgres://{}:{}@{}/postgres'.format(
            _DEFAULT_POSTGRES_USER,
            _DEFAULT_POSTGRES_PASS,
            ip_port
        )

    return result


def ip_colon_port(ip, port):
    # type: (str, int) -> str

    return '{}:{}'.format(ip, port)

if __name__ == '__main__':
    dotenv = load_config(DOTENV_FILE)

    docker_ip = get_docker_ip()

    dotenv[DATABASE_URL] = set_or_adjust_database(
        dotenv.get(DATABASE_URL, ''),
        docker_ip,
        get_docker_compose_port('postgresql', 5432)
    )
    dotenv[ELASTICSEARCH_KEY] = ip_colon_port(docker_ip, get_docker_compose_port('elasticsearch', 9200))

    write_config(dotenv, DOTENV_FILE)
