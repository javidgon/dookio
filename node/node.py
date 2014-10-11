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


def get_port():
    """
    Assings a 'non-used' port.
    """
    if os.path.exists("USED_PORTS"):
        with open('USED_PORTS') as f:
            used_ports = [int(line.rstrip()) for line in f]
    else:
        open('USED_PORTS', 'w')
        used_ports = []
 
    for port in range(STARTING_PORT, ENDING_PORT):
        if port not in used_ports:
            with open('USED_PORTS', 'a') as f:
    	        f.write('{}\n'.format(port))
	    return int(port)
    raise Exception('There are no more available ports!')

@Request.application
def application(request):
    """
    Creates and configures a docker image/container for a certain Dockerfile.
    This Dockerfile is fetched from a remote machine (a.k.a SERVER), properly configured with
    the "gitreceive" library. Please notice that the code path in that remote
    machine has to match with the pattern defined in the env vars.
    """
    # Fetch get params
    user = request.args.get('user')
    repo = request.args.get('repo')
    tag = "{}/{}".format(user, repo)

    # Set paths
    local_path = '{}/{}/{}'.format(LOCAL_ROOT_DIRECTORY, user, repo)
    remote_path = '{}/{}/{}'.format(SERVER_ROOT_DIRECTORY, user, repo)
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
    # Create docker socket
    cli = docker.Client(base_url='unix://var/run/docker.sock',
                        version='1.12',
                        timeout=10)
    # Build docker image
    try:
        image = cli.build(path=local_path, tag=tag)
        for instruction in image:
            print instruction
    except:
	cli.remove_image(image)
    # Create container (at this point only the port 80 will be open)
    try:
        container = cli.create_container(image=tag, command="", ports=[80])
        # Start container
        port = get_port()
        # Register new port into file
        result = cli.start(container=container.get('Id'), port_bindings={80: port})
    except:
        cli.remove_container(container, v=False, link=False)
    else:
        return Response(
	    json.dumps({'id': container.get('Id'),
                        'port': '{}'.format(port)}))
    return Response(status="500")

if __name__ == '__main__':
    from werkzeug.serving import run_simple
    run_simple('0.0.0.0', 5000, application)
