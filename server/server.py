import os
import redis
import requests
import json
import random

from werkzeug.wrappers import Request, Response

DOMAIN = os.environ['DOOKIO_DOMAIN']

def get_nodes():
    with open('NODES') as f:
        nodes = [line.rstrip() for line in f]
    return nodes

def pick_up_node():
    nodes = get_nodes()
    idx = random.randint(0, len(nodes) - 1)
    return nodes[idx]

def fetch_apps(redis_cli):
    apps = {}
    for app in redis_cli.scan_iter():
        apps[app] = redis_cli.lrange(app, 1, -1)
    return apps

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
    user = request.args.get('user')
    repo = request.args.get('repo')

    # Dookio-cli: apps command
    if request.path == '/apps':
        apps = fetch_apps(redis_cli)
        return Response(
            [('--> {} (replicated in {} containers)\n'.format(
                app[app.find(":") + 1:], len(apps[app]))) for app in apps])

    # Dookio-cli: containers command
    elif request.path == '/containers':
        nodes = {}
        for node in get_nodes():
             response = requests.get('{}:5000/containers?user={}&repo={}'.format(node, user, repo))
             nodes[node] = json.loads(response.content)
	resp = [{
	    'node': node,
            'containers': [container.get('Id') for container in containers]
	} for node, containers in nodes.iteritems()]
        return Response(json.dumps(resp))

    # Pick up the proper params
    address = '{}.{}.{}'.format(repo, user, DOMAIN)

    if not all([user, repo]):
        return Response(
            'There was a problem. Please be sure you are providing both "user", "repo"\n')

    # Set up docker container
    node = pick_up_node()
    response = requests.get('{}:5000'.format(node),
                            params={'user': user, 'repo': repo})

    if response.status_code == 200:
        # Set up hipache webserver for the specified branch
        container_info = json.loads(response.content)
        repo_key = 'frontend:{}'.format(address)
        if not redis_cli.lrange(repo_key, 0, -1):
            redis_cli.rpush(repo_key, repo)
        redis_cli.rpush(repo_key, '{}:{}'.format(node, container_info.get('port')))

        return Response(
        'App successfully deployed! Go to http://{}\n'.format(
            address))
    else:
        return Response(
        'Something went wrong! Please check your Dockerfile. \n')

if __name__ == '__main__':
    from werkzeug.serving import run_simple
    run_simple('0.0.0.0', 8000, application)
