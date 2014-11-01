import docker
import os
import json
import tarfile

from werkzeug.wrappers import Request, Response
from paramiko import SSHClient, AutoAddPolicy
from scp import SCPClient

from .utils import (
    create_container,
    start_container,
    stop_containers,
    get_containers,
    create_image,
    remove_image)

SERVER_MACHINE_ADDRESS = os.environ['DOOKIO_SERVER_ADDRESS']
SERVER_USERNAME = os.environ['DOOKIO_SERVER_USER']
SERVER_USERNAME_PASSWORD = os.environ['DOOKIO_SERVER_USER_PASSWORD']
SERVER_ROOT_DIRECTORY = os.environ['DOOKIO_SERVER_ROOT']
LOCAL_ROOT_DIRECTORY = os.environ['DOOKIO_NODE_ROOT']


@Request.application
def application(request):
    """
    Creates and configures a docker image/container for a certain Dockerfile.
    This Dockerfile is fetched from a remote machine (a.k.a SERVER),
    properly configured with the "gitreceive" library.
    Please notice that the code path in that remote
    machine has to match with the pattern defined in the env vars.
    """
    # Create docker socket
    cli = docker.Client(base_url='unix://var/run/docker.sock',
                        version='1.12',
                        timeout=10)

    conf = {
        'action': request.args.get('action'),
        'path': request.path,
        'user': request.args.get('user'),
        'repo': request.args.get('repo'),
        'local_path': '{}/{}/{}'.format(
            LOCAL_ROOT_DIRECTORY,
            request.args.get('user'),
            request.args.get('repo')),
        'remote_path': '{}/{}/{}'.format(
            SERVER_ROOT_DIRECTORY,
            request.args.get('user'),
            request.args.get('repo'))
    }

    # Extract some values from the conf dict.
    action = conf.get('action')
    path = conf.get('path')
    local_path = conf.get('local_path')
    remote_path = conf.get('remote_path')

    if path == '/containers':
        containers = []
        if action == 'get':
            containers = get_containers(cli, conf)
        elif action == 'stop':
            try:
                stop_containers(cli, conf)
            except Exception, e:
                return Response(str(e), status=400)
        elif action == 'start':
            try:
                containers = start_container(cli, conf)
            except Exception, e:
                return Response(str(e), status=400)
        elif action == 'remove':
            stop_containers(cli, conf)
            remove_image(cli, conf)

        return Response(json.dumps(containers))

    if not os.path.exists(local_path):
        os.makedirs(local_path)

    # Establish ssh connection
    ssh = SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(AutoAddPolicy())
    ssh.connect(SERVER_MACHINE_ADDRESS,
                username=SERVER_USERNAME,
                password=SERVER_USERNAME_PASSWORD)
    scp = SCPClient(ssh.get_transport())
    # Fetch code from server
    scp.get('{}/code.tar.gz'.format(remote_path), local_path)
    # Extract files
    with tarfile.open("{}/code.tar.gz".format(local_path), 'r:gz') as f:
        f.extractall('{}'.format(local_path))

    create_image(cli, conf)
    try:
        container, port = create_container(cli, conf)
    except Exception, e:
        return Response(str(e), status=400)
    else:
        return Response(
            json.dumps({'id': container.get('Id'),
                        'port': '{}'.format(port)}))
