import os

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
        container = cli.create_container(
            name="{}_{}_{}".format(user, repo, port),
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
    containers = get_containers(cli, conf)
    for cont in containers:
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
        # The containers name: e.g /git_apache_4567 (With /)).
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
