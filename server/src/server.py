import os
import redis
import requests
import json

from werkzeug.wrappers import Request, Response

from src.utils import (fetch_apps,
                       contact_nodes,
                       was_applied,
                       exist_application,
                       add_app_to_webserver_routing,
                       remove_app_from_webserver_routing,
                       add_container_to_webserver_routing,
                       pick_up_node)


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
    DOMAIN = os.environ.get('DOOKIO_DOMAIN', 'localhost')
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
        conf['action'] = None
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
                                                   container.get('port'),
                                                   conf)
            else:
                return Response(response.content, status=response.status_code)

        return Response(
            'App successfully deployed! Go to http://{}\n'.format(
                conf.get('application_address')))
    else:
        return Response(
            'Something went wrong! Are you using the proper parameters?. \n')
