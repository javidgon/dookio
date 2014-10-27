import random
import os
import json
import requests

dir = os.path.dirname(__file__)

def get_nodes():
    """
    Get all the available nodes.
    """
    with open(os.path.join(dir, 'NODES')) as f:
        nodes = [line.rstrip() for line in f]
    return nodes


def pick_up_node():
    """
    Pick a random node.
    """
    nodes = get_nodes()
    idx = random.randint(0, len(nodes) - 1)
    return nodes[idx]


def fetch_apps(redis_cli):
    """
    Fetch all the deployed applications.
    """
    apps = {}
    for app in redis_cli.scan_iter():
        apps[app] = redis_cli.lrange(app, 1, -1)
    return apps


def contact_nodes(conf):
    """
    Contact all nodes in order to apply actions.
    """
    user = conf.get('user')
    repo = conf.get('repo')
    action = conf.get('action')

    nodes = {}
    for node in get_nodes():
        response = contact_containers(action, node, user, repo)
        if response.status_code == 200:
            clean_content = json.loads(response.content)
            nodes[node] = (clean_content, 200)
        else:
            nodes[node] = (response.content, response.status_code)
    return nodes


def contact_containers(action, node, user, repo):
    """
    Contact with the different containers spread in a certain node.
    """
    response = requests.get(
        '{}:5000/containers?action={}&user={}&repo={}'.format(
            node, action, user, repo))
    return response


def add_app_to_webserver_routing(redis_cli, conf):
    repo = conf.get('repo')
    application_address = conf.get('application_address')
    webserver_application_name = 'frontend:{}'.format(application_address)
    redis_cli.rpush(webserver_application_name, repo)


def remove_app_from_webserver_routing(redis_cli, conf):
    application_address = conf.get('application_address')
    redis_cli.delete('frontend:{}'.format(application_address))


def exist_application(redis_cli, conf):
    application_address = conf.get('application_address')
    webserver_application_name = 'frontend:{}'.format(application_address)
    return bool(redis_cli.lrange(webserver_application_name, 0, -1))


def add_container_to_webserver_routing(redis_cli, node, port, conf):
    application_address = conf.get('application_address')
    webserver_application_name = 'frontend:{}'.format(
        application_address)
    redis_cli.rpush(webserver_application_name, '{}:{}'.format(node, port))


def was_applied(response_nodes):
    """
    Was applied in at least one node?
    """
    for node_ip, response in response_nodes.iteritems():
        status_code = response[1]
        if status_code == 200:
            return True
    return False
