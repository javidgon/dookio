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
    used_ports, lines = read_used_ports()
    f = open('AUX_USED_PORTS', 'w')
    for line in lines:
        if port != int(line.rstrip()):
            f.write(line)
    f.close()
    os.rename('AUX_USED_PORTS', 'USED_PORTS')

@Request.application
def application(request):
    """
    Creates and configures a docker image/container for a certain Dockerfile.
    This Dockerfile is fetched from a remote machine (a.k.a SERVER), properly configured with
    the "gitreceive" library. Please notice that the code path in that remote
    machine has to match with the pattern defined in the env vars.
    """
    # Create docker socket
    cli = docker.Client(base_url='unix://var/run/docker.sock',
                        version='1.12',
                        timeout=10)

    # Fetch get params
    action = request.args.get('action')
    user = request.args.get('user')
    repo = request.args.get('repo')
    tag = "{}/{}".format(user, repo)

    # Set paths
    local_path = '{}/{}/{}'.format(LOCAL_ROOT_DIRECTORY, user, repo)
    remote_path = '{}/{}/{}'.format(SERVER_ROOT_DIRECTORY, user, repo)

    # Get list of containers.
    if request.path == '/containers':
        containers = []
        if action == 'get':
            for cont in cli.containers():
		name = cont.get('Names')[0]
                if '{}_{}'.format(user, repo) == name[1:len(name) - 5]:
                    containers.append(cont)
        elif action == 'stop':
            for cont in cli.containers():
		name = cont.get('Names')[0]
                if '{}_{}'.format(user, repo) == name[1:len(name) - 5]:
                    ports = cont.get('Ports')
                    for port in ports:
                        make_port_available(port.get('PublicPort'))
                    cli.kill(cont)
                    cli.remove_container(cont.get('Id'), force=True)
                    for image in cli.images():
                        if '{}/{}'.format(user, repo) in image.get('RepoTags')[0]:
                            try:
                                cli.remove_image(image.get('Id'), force=True)
                            except:
                                pass

        return Response(json.dumps(containers))

    if not os.path.exists(local_path):
        os.makedirs(local_path)

    # Establish ssh connection
    ssh = SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(AutoAddPolicy())
    ssh.connect(SERVER_MACHINE_ADDRESS, username=SERVER_USERNAME, password=SERVER_USERNAME_PASSWORD)
    scp = SCPClient(ssh.get_transport())
    # Fetch code from server
    scp.get('{}/code.tar.gz'.format(remote_path), local_path)
    # Extract files
    with tarfile.open("{}/code.tar.gz".format(local_path), 'r:gz') as f:
        f.extractall('{}'.format(local_path))
    # Build docker image
    image = cli.build(path=local_path, tag=tag)
    for instruction in image:
        print instruction

    # Start container
    port = get_port()
    # Create container (at this point only the port 80 will be open)
    container = cli.create_container(name="{}_{}_{}".format(user, repo, port),
                                     image=tag,
                                     command="",
                                     ports=[80])
    # Register new port into file
    result = cli.start(container=container.get('Id'), port_bindings={80: port})
    return Response(
        json.dumps({'id': container.get('Id'),
                    'port': '{}'.format(port)}))

if __name__ == '__main__':
    from werkzeug.serving import run_simple
    run_simple('0.0.0.0', 5000, application)
