import os
import redis
import requests
import json
import random

from werkzeug.wrappers import Request, Response

DOMAIN = os.environ['DOOKIO_DOMAIN']


def get_nodes():
    """
    Get all the available nodes.
    """
    with open('NODES') as f:
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
    Contact all nodes in order to do apply actions.
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
        body = response[0]
        status_code = response[1]
        if status_code == 200:
            return True
    return False


@Request.application
def application(request):
    """
    Set up the infrastructure required for Heroku-ish app deployment.
    This setting uses Hipache/Redis as webserver and load balancer, and Docker
    as app container. Please be aware that the docker configuration is done in
    the different nodes (node.py).

    The standard configuration chooses one node of the list defined above,
    and provides him with the required information for a success deployment
    (user & repo params).
    """
    redis_cli = redis.StrictRedis(host='localhost', port=6379, db=0)

    # Dookio-cli: apps command
    if request.path == '/apps':
        apps = fetch_apps(redis_cli)
        return Response(
            [('--> {} (replicated in {} containers)\n'.format(
                app[app.find(":") + 1:], len(apps[app]))) for app in apps])

    # Pick up the proper params
    conf = {
        'action': request.args.get('action'),
        'multiplicator': int(request.args.get('multiplicator', 1)),
        'user': request.args.get('user'),
        'repo': request.args.get('repo'),
        'application_address': '{}.{}.{}'.format(
            request.args.get('repo'), request.args.get('user'), DOMAIN)
    }

    if not all([conf.get('user'), conf.get('repo')]):
        return Response(
            'There was a problem. Please be sure you are '
            'providing both "user", "repo"\n')

    # Dookio-cli: containers command
    action = conf.get('action')
    if request.path == '/containers':
        response_nodes = contact_nodes(conf)
        if action == 'stop':
            if was_applied(response_nodes):
                remove_app_from_webserver_routing(redis_cli, conf)
        elif action == 'start':
            if (was_applied(response_nodes) and
                    not exist_application(redis_cli, conf)):
                add_app_to_webserver_routing(redis_cli, conf)
            for node_ip, response in response_nodes.iteritems():
                # We only want to iterate over the valid responses.
                status_code = response[1]
                body = response[0][0]
                if status_code == 200:
                    port = body.get('Ports')[0].get('PublicPort')
                    add_container_to_webserver_routing(redis_cli,
                                                       node_ip,
                                                       port,
                                                       conf)
        resp = [{
            'node': node_ip,
            'containers': content[0]
        } for node_ip, content in response_nodes.iteritems()]
        return Response(json.dumps(resp))

    # Dookio-cli: scale command
    if request.path == '/scale':
        if not exist_application(redis_cli, conf):
            return Response(
                'The app can not scale unless is running!\n')

    if request.path == '/scale' or request.path == '/':
        user = conf.get('user')
        repo = conf.get('repo')
        # Stop all existing containers
        conf['action'] = 'stop'
        contact_nodes(conf)
        remove_app_from_webserver_routing(redis_cli, conf)
        for i in range(conf.get('multiplicator')):
            node = pick_up_node()
            response = requests.get('{}:5000'.format(node),
                                    params={'user': user, 'repo': repo})

            if response.status_code == 200:
                # Set up hipache webserver for the specified branch
                container = json.loads(response.content)
                if not exist_application(redis_cli, conf):
                    add_app_to_webserver_routing(redis_cli, conf)
                add_container_to_webserver_routing(redis_cli,
                                                   node,
                                                   container.get('Port'),
                                                   conf)
            else:
                return Response(response.content, status=response.status_code)

        return Response(
            'App successfully deployed! Go to http://{}\n'.format(
                conf.get('application_address')))
    else:
        return Response(
            'Something went wrong! Are you using the proper parameters?. \n')

if __name__ == '__main__':
    from werkzeug.serving import run_simple
    run_simple('0.0.0.0', 8000, application)
