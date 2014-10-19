import docker
import os
import json
import tarfile

from werkzeug.wrappers import Request, Response
from paramiko import SSHClient, AutoAddPolicy
from scp import SCPClient

SERVER_MACHINE_ADDRESS = os.environ['DOOKIO_SERVER_ADDRESS']
SERVER_USERNAME = os.environ['DOOKIO_SERVER_USER']
SERVER_USERNAME_PASSWORD = os.environ['DOOKIO_SERVER_USER_PASSWORD']
SERVER_ROOT_DIRECTORY = os.environ['DOOKIO_SERVER_ROOT']
LOCAL_ROOT_DIRECTORY = os.environ['DOOKIO_NODE_ROOT']
STARTING_PORT = 4567
ENDING_PORT = 4700


def read_used_ports():
    """
    Read the used ports from the USED_PORTS file.
    """
    lines = []
    if os.path.exists("USED_PORTS"):
        with open('USED_PORTS') as f:
            lines = [line for line in f]
            used_ports = [int(line.rstrip()) for line in lines]
    else:
        f = open('USED_PORTS', 'w')
        f.close()
        used_ports = []
    return used_ports, lines


def get_port():
    """
    Assings a 'non-used' port.
    """
    used_ports, _ = read_used_ports()
    for port in range(STARTING_PORT, ENDING_PORT):
        if port not in used_ports:
            with open('USED_PORTS', 'a') as f:
                f.write('{}\n'.format(port))
            return int(port)
    raise Exception('There are no more available ports!')


def make_port_available(port):
    """
    Free up recently used port.
    """
    used_ports, lines = read_used_ports()
    f = open('AUX_USED_PORTS', 'w')
    for line in lines:
        if port != int(line.rstrip()):
            f.write(line)
    f.close()
    os.rename('AUX_USED_PORTS', 'USED_PORTS')


def _reserve_container(cli, conf):
    """
    Reserve container.
    """
    user = conf.get('user')
    repo = conf.get('repo')
    tag = "{}/{}".format(conf.get('user'), conf.get('repo'))

    port = get_port()
    try:
        # Create container (at this point only the port 80 will be open)
        container = cli.create_container(name="{}_{}_{}".format(user, repo, port),
                                         image=tag,
                                         command="",
                                         ports=[80])
        # Register new port into file
        cli.start(container=container.get('Id'), port_bindings={80: port})
    except:
        make_port_available(port)
        raise
    else:
        return container, port


def create_container(cli, conf):
    """
    Create container from scratch.
    """
    try:
        container, port = _reserve_container(cli, conf)
    except:
        raise Exception(
            'The container could not be create. '
            'Was the image properly create?.')
    else:
        return container, port


def start_container(cli, conf):
    """
    Start an stopped container.
    """
    if get_containers(cli, conf):
        raise Exception(
            'Sorry but there is already a running container. '
            'Use "scale" instead.')
    try:
        container, port = _reserve_container(cli, conf)
    except:
        raise Exception(
            'You cannot start an unexisting app. '
            'Please do "git push" before.')
    else:
        return get_containers(cli, conf)


def stop_containers(cli, conf):
    """
    Stop and kill containers associated with the user/repo application.
    Note: It doesn't remove the image. So the containers can be recreated
    with easy.
    """
    user = conf.get('user')
    repo = conf.get('repo')
    exist = False
    for cont in cli.containers():
        # The full application name.
        name = cont.get('Names')[0]
        # The name without the 'frontend:' string.
        clean_name = name[1:len(name) - 5]
        if '{}_{}'.format(user, repo) == clean_name:
            exist = True
            ports = cont.get('Ports')
            for port in ports:
                make_port_available(port.get('PublicPort'))
            cli.kill(cont)
            try:
                cli.remove_container(cont.get('Id'), force=True)
            except:
                # When the container is currently blocked.
                pass

    if not exist:
        raise Exception('{}/{} is not running!'.format(user, repo))

def get_containers(cli, conf):
    """
    Get all the active containers for a certain user/repo application.
    """
    user = conf.get('user')
    repo = conf.get('repo')

    containers = []
    for cont in cli.containers():
        # The full application name.
        name = cont.get('Names')[0]
        # The name without the 'frontend:' string.
        clean_name = name[1:len(name) - 5]
        if '{}_{}'.format(user, repo) == clean_name:
            containers.append(cont)
    return containers


def create_image(cli, conf):
    """
    Create an image for the application.
    """
    local_path = conf.get('local_path')
    tag = "{}/{}".format(conf.get('user'), conf.get('repo'))

    # Build docker image
    image = cli.build(path=local_path, tag=tag)
    for instruction in image:
        print instruction
    return image


def remove_image(cli, conf):
    """
    Remove the image for the user/repo application.
    """
    user = conf.get('user')
    repo = conf.get('repo')

    for image in cli.images():
        if '{}/{}'.format(user, repo) in image.get('RepoTags')[0]:
            try:
                cli.remove_image(image.get('Id'), force=True)
            except:
                # This means that the image was already removed.
                pass


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

if __name__ == '__main__':
    from werkzeug.serving import run_simple
    run_simple('0.0.0.0', 5000, application)
