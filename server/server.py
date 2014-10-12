import os
import redis
import requests
import json
import random

from werkzeug.wrappers import Request, Response

DOMAIN = os.environ['DOOKIO_DOMAIN']


def pick_up_node():
    with open('NODES') as f:
        nodes = [line.rstrip() for line in f]

    idx = random.randint(0, len(nodes) - 1)
    return nodes[idx]


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
    # Pick up the proper params
    user = request.args.get('user')
    repo = request.args.get('repo')
    address = '{}.{}'.format(repo, DOMAIN)

    if not all([user, repo]):
        return Response(
            'There was a problem. Please be sure you are providing both "user", "repo"\n')

    r = redis.StrictRedis(host='localhost', port=6379, db=0)
    # Set up docker container
    node = pick_up_node()
    response = requests.get('{}:5000'.format(node),
                            params={'user': user, 'repo': repo})

    if response.status_code == 200:
        # Set up hipache webserver for the specified branch
        container_info = json.loads(response.content)
        repo_key = 'frontend:{}'.format(address)
        r.rpush(repo_key, repo)
        r.rpush(repo_key, '{}:{}'.format(node, container_info.get('port')))

        return Response(
        'App successfully deployed! Go to http://{}\n'.format(
            address))
    else:
        return Response(
        'Something went wrong! Please check your Dockerfile. \n')

if __name__ == '__main__':
    from werkzeug.serving import run_simple
    run_simple('0.0.0.0', 8000, application)
