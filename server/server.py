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

def contact_containers(action, user, repo):
    """
    Contact with the different comtainers.
    """
    nodes = {}
    for node in get_nodes():
        response = requests.get(
            '{}:5000/containers?action={}&user={}&repo={}'.format(
                node, action, user, repo))
        nodes[node] = json.loads(response.content)
    return nodes


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
    action = request.args.get('action')
    multiplicator = int(request.args.get('multiplicator', 1))
    user = request.args.get('user')
    repo = request.args.get('repo')
    address = '{}.{}.{}'.format(repo, user, DOMAIN)
    repo_key = 'frontend:{}'.format(address)

    if not all([user, repo]):
        return Response(
            'There was a problem. Please be sure you are providing both "user", "repo"\n')

    # Dookio-cli: containers command
    if request.path == '/containers':
        nodes = contact_containers(action, user, repo)
	resp = [{
            'node': node,
            'containers': [container.get('Id') for container in containers]
	} for node, containers in nodes.iteritems()]
        if action == 'stop':
            redis_cli.delete('frontend:{}'.format(address))

        return Response(json.dumps(resp))

    # Dookio-cli: scale command
    if request.path == '/scale':
        if not redis_cli.lrange(repo_key, 0, -1):
            return Response(
                'The app can not scale unless is running!\n')
    if request.path == '/scale' or request.path == '/':
        # Stop all existing containers
        nodes = contact_containers('stop', user, repo)
        redis_cli.delete('frontend:{}'.format(address))
        for i in range(multiplicator):
            node = pick_up_node()
            response = requests.get('{}:5000'.format(node),
                                    params={'user': user, 'repo': repo})

            if response.status_code == 200:
                # Set up hipache webserver for the specified branch
                container_info = json.loads(response.content)
                if not redis_cli.lrange(repo_key, 0, -1):
                    redis_cli.rpush(repo_key, repo)
                redis_cli.rpush(repo_key, '{}:{}'.format(node, container_info.get('port')))
            else:
                return Response(
                'Something went wrong! Please check your Dockerfile. \n')

        return Response(
            'App successfully deployed! Go to http://{}\n'.format(
               address))
    else:
        return Response(
        'Something went wrong! Are you using the proper parameters?. \n')

if __name__ == '__main__':
    from werkzeug.serving import run_simple
    run_simple('0.0.0.0', 8000, application)
