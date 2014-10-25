import unittest
import json
from mock import patch
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from src.server import application


class ServerApplicationTestSuite(unittest.TestCase):
    def expected_conf(self, conf):
        return {
            'action': conf.get('action'),
            'multiplicator': int(conf.get('multiplicator', '1')),
            'user': conf.get('user'),
            'repo': conf.get('repo'),
            'application_address': '{}.{}.{}'.format(
                conf.get('repo'), conf.get('user'), 'localhost')
        }

    def setUp(self):
        self.nodes = ['http://0.0.0.0', 'http://123.123.123.123']
        self.c = Client(application, BaseResponse)

    @patch.dict('os.environ', {'DOOKIO_DOMAIN': 'localhost'})
    @patch('src.server.redis')
    def test_application_returns_deployed_applications_when_there_is_one(
            self, mock_redis):
        mock_redis.StrictRedis.return_value.scan_iter.return_value = [
            'frontend:apache.git.example.com']
        response = self.c.get('/apps')

        assert response.status_code == 200
        assert 'apache.git.example.com' in response.data

    @patch.dict('os.environ', {'DOOKIO_DOMAIN': 'localhost'})
    @patch('src.server.redis')
    def test_application_returns_deployed_applications_when_there_is_none(
            self, mock_redis):
        mock_redis.StrictRedis.return_value.scan_iter.return_value = []
        response = self.c.get('/apps')

        assert response.status_code == 200
        assert '' == response.data

    def test_error_message_when_repo_paramemer_is_missing(self):
        response = self.c.get('/?user={}'.format('git'))

        assert response.status_code == 200
        assert 'problem' in response.data

    def test_error_message_when_user_paramemer_is_missing(self):
        response = self.c.get('/?repo={}'.format('apache'))

        assert response.status_code == 200
        assert 'problem' in response.data

    def test_error_message_when_both_paramemers_are_missing(self):
        response = self.c.get('/')

        assert response.status_code == 200
        assert 'problem' in response.data

    @patch.dict('os.environ', {'DOOKIO_DOMAIN': 'localhost'})
    @patch('src.server.redis')
    @patch('src.server.contact_nodes')
    @patch('src.server.was_applied')
    @patch('src.server.remove_app_from_webserver_routing')
    def test_when_the_stop_action_for_containers_is_provided(
            self, mock_remove_app, mock_was_applied,
            mock_contact_nodes, mock_redis):
        conf = {
            'action': 'stop',
            'user': 'git',
            'repo': 'apache',
        }

        content = {
            node: {
                'node': node
            } for node in self.nodes}

        response_nodes = {
            node: (content, 200)
            for node, content in content.iteritems()}

        mock_contact_nodes.return_value = response_nodes
        mock_was_applied.return_value = response_nodes
        response = self.c.get('/containers?action={}&user={}&repo={}'.format(
            conf.get('action'), conf.get('user'), conf.get('repo')))

        expected_resp = [{
            'node': node_ip,
            'containers': body[0]
        } for node_ip, body in response_nodes.iteritems()]

        assert response.status_code == 200
        assert json.loads(response.data) == expected_resp
        mock_remove_app.assert_called_once_with(
            mock_redis.StrictRedis(), self.expected_conf(conf))
        mock_was_applied.assert_called_once_with(response_nodes)
        mock_contact_nodes.assert_called_once_with(self.expected_conf(conf))

    @patch.dict('os.environ', {'DOOKIO_DOMAIN': 'localhost'})
    @patch('src.server.redis')
    @patch('src.server.exist_application')
    @patch('src.server.contact_nodes')
    @patch('src.server.was_applied')
    @patch('src.server.add_app_to_webserver_routing')
    @patch('src.server.add_container_to_webserver_routing')
    def test_start_action_for_containers_and_app_exists(
            self, mock_add_container, mock_add_app, mock_was_applied,
            mock_contact_nodes, mock_exist_application, mock_redis):
        port = 4567
        conf = {
            'action': 'start',
            'user': 'git',
            'repo': 'apache',
        }

        content = ({
            node: [{
                'node': node,
                'Ports': [{'PublicPort': port}]}, ]
            for node in self.nodes}, )

        response_nodes = {
            node: (content, 200)
            for node, content in content[0].iteritems()}

        mock_contact_nodes.return_value = response_nodes
        mock_was_applied.return_value = True
        mock_exist_application.return_value = True
        response = self.c.get('/containers?action={}&user={}&repo={}'.format(
            conf.get('action'), conf.get('user'), conf.get('repo')))

        expected_resp = [{
            'node': node_ip,
            'containers': body[0]
        } for node_ip, body in response_nodes.iteritems()]

        assert response.status_code == 200
        assert json.loads(response.data) == expected_resp
        assert mock_add_container.call_count == 2
        assert not mock_add_app.called
        mock_was_applied.assert_called_once_with(response_nodes)
        mock_exist_application.assert_called_once_with(
            mock_redis.StrictRedis(), self.expected_conf(conf))
        mock_contact_nodes.assert_called_once_with(self.expected_conf(conf))

    @patch.dict('os.environ', {'DOOKIO_DOMAIN': 'localhost'})
    @patch('src.server.redis')
    @patch('src.server.exist_application')
    @patch('src.server.contact_nodes')
    @patch('src.server.was_applied')
    @patch('src.server.add_app_to_webserver_routing')
    @patch('src.server.add_container_to_webserver_routing')
    def test_start_action_for_containers_app_does_not_exist(
            self, mock_add_container, mock_add_app, mock_was_applied,
            mock_contact_nodes, mock_exist_application, mock_redis):
        port = 4567
        conf = {
            'action': 'start',
            'user': 'git',
            'repo': 'apache',
        }

        content = ({
            node: [{
                'node': node,
                'Ports': [{'PublicPort': port}]}, ]
            for node in self.nodes}, )

        response_nodes = {
            node: (content, 200)
            for node, content in content[0].iteritems()}

        mock_contact_nodes.return_value = response_nodes
        mock_was_applied.return_value = True
        mock_exist_application.return_value = False
        response = self.c.get('/containers?action={}&user={}&repo={}'.format(
            conf.get('action'), conf.get('user'), conf.get('repo')))

        expected_resp = [{
            'node': node_ip,
            'containers': body[0]
        } for node_ip, body in response_nodes.iteritems()]

        assert response.status_code == 200
        assert json.loads(response.data) == expected_resp
        assert mock_add_container.call_count == 2
        mock_add_app.assert_called_once_with(
            mock_redis.StrictRedis(), self.expected_conf(conf))
        mock_was_applied.assert_called_once_with(response_nodes)
        mock_exist_application.assert_called_once_with(
            mock_redis.StrictRedis(), self.expected_conf(conf))
        mock_contact_nodes.assert_called_once_with(self.expected_conf(conf))

    @patch.dict('os.environ', {'DOOKIO_DOMAIN': 'localhost'})
    @patch('src.server.redis')
    @patch('src.server.exist_application')
    def test_scale_app_if_it_is_not_running(
            self, mock_exist_application, mock_redis):
        conf = {
            'user': 'git',
            'repo': 'apache',
            'multiplicator': 2,
        }

        mock_exist_application.return_value = False
        response = self.c.get('/scale?multiplicator={}&user={}&repo={}'.format(
            conf.get('multiplicator'), conf.get('user'), conf.get('repo')))

        assert response.status_code == 200
        assert 'The app can not scale unless is running!' in response.data
        mock_exist_application.assert_called_once_with(
            mock_redis.StrictRedis(), self.expected_conf(conf))

    @patch.dict('os.environ', {'DOOKIO_DOMAIN': 'localhost'})
    @patch('src.server.redis')
    @patch('src.server.requests')
    @patch('src.server.contact_nodes')
    @patch('src.server.remove_app_from_webserver_routing')
    @patch('src.server.pick_up_node')
    @patch('src.server.exist_application')
    @patch('src.server.add_app_to_webserver_routing')
    @patch('src.server.add_container_to_webserver_routing')
    def test_normal_app_push_if_app_does_not_exist(
            self, mock_add_container, mock_add_app, mock_exist_application,
            mock_pick_up_node, mock_remove_app, mock_contact_nodes,
            mock_requests, mock_redis):
        conf = {
            'user': 'git',
            'repo': 'apache'
        }

        node = self.nodes[0]
        port = 4567
        mock_exist_application.return_value = False
        mock_requests.get.return_value.status_code = 200
        mock_requests.get.return_value.content = json.dumps({'port': port})
        mock_pick_up_node.return_value = node
        response = self.c.get('/?user={}&repo={}'.format(
            conf.get('user'), conf.get('repo')))

        assert response.status_code == 200
        assert self.expected_conf(conf).get(
            'application_address') in response.data
        mock_contact_nodes.assert_called_once_with(self.expected_conf(conf))
        mock_remove_app.assert_called_once_with(
            mock_redis.StrictRedis(), self.expected_conf(conf))
        mock_pick_up_node.assert_called_once_with()
        mock_exist_application.assert_called_once_with(
            mock_redis.StrictRedis(), self.expected_conf(conf))
        mock_add_app.assert_called_once_with(
            mock_redis.StrictRedis(), self.expected_conf(conf))
        mock_add_container.assert_called_once_with(
            mock_redis.StrictRedis(), node, port, self.expected_conf(conf))

    @patch.dict('os.environ', {'DOOKIO_DOMAIN': 'localhost'})
    @patch('src.server.redis')
    @patch('src.server.requests')
    @patch('src.server.contact_nodes')
    @patch('src.server.remove_app_from_webserver_routing')
    @patch('src.server.pick_up_node')
    @patch('src.server.exist_application')
    @patch('src.server.add_app_to_webserver_routing')
    @patch('src.server.add_container_to_webserver_routing')
    def test_normal_app_push_if_app_does_exist(
            self, mock_add_container, mock_add_app, mock_exist_application,
            mock_pick_up_node, mock_remove_app, mock_contact_nodes,
            mock_requests, mock_redis):
        conf = {
            'user': 'git',
            'repo': 'apache'
        }

        node = self.nodes[0]
        port = 4567
        mock_exist_application.return_value = True
        mock_requests.get.return_value.status_code = 200
        mock_requests.get.return_value.content = json.dumps({'port': port})
        mock_pick_up_node.return_value = node
        response = self.c.get('/?user={}&repo={}'.format(
            conf.get('user'), conf.get('repo')))

        assert response.status_code == 200
        assert self.expected_conf(conf).get(
            'application_address') in response.data
        mock_contact_nodes.assert_called_once_with(self.expected_conf(conf))
        mock_remove_app.assert_called_once_with(
            mock_redis.StrictRedis(), self.expected_conf(conf))
        mock_pick_up_node.assert_called_once_with()
        mock_exist_application.assert_called_once_with(
            mock_redis.StrictRedis(), self.expected_conf(conf))
        assert not mock_add_app.called
        mock_add_container.assert_called_once_with(
            mock_redis.StrictRedis(), node, port, self.expected_conf(conf))

    @patch.dict('os.environ', {'DOOKIO_DOMAIN': 'localhost'})
    @patch('src.server.redis')
    @patch('src.server.requests')
    @patch('src.server.contact_nodes')
    @patch('src.server.remove_app_from_webserver_routing')
    @patch('src.server.pick_up_node')
    @patch('src.server.exist_application')
    @patch('src.server.add_app_to_webserver_routing')
    @patch('src.server.add_container_to_webserver_routing')
    def test_normal_app_push_if_node_returns_400(
            self, mock_add_container, mock_add_app, mock_exist_application,
            mock_pick_up_node, mock_remove_app, mock_contact_nodes,
            mock_requests, mock_redis):
        conf = {
            'user': 'git',
            'repo': 'apache'
        }

        node = self.nodes[0]
        mock_requests.get.return_value.status_code = 400
        mock_requests.get.return_value.content = 'Node unreachable'
        mock_pick_up_node.return_value = node
        response = self.c.get('/?user={}&repo={}'.format(
            conf.get('user'), conf.get('repo')))

        assert response.status_code == 400
        assert 'Node unreachable' in response.data
        mock_contact_nodes.assert_called_once_with(self.expected_conf(conf))
        mock_remove_app.assert_called_once_with(
            mock_redis.StrictRedis(), self.expected_conf(conf))
        mock_pick_up_node.assert_called_once_with()
        assert not mock_exist_application.called
        assert not mock_add_app.called
        assert not mock_add_container.called

    @patch.dict('os.environ', {'DOOKIO_DOMAIN': 'localhost'})
    @patch('src.server.redis')
    @patch('src.server.requests')
    @patch('src.server.contact_nodes')
    @patch('src.server.remove_app_from_webserver_routing')
    @patch('src.server.pick_up_node')
    @patch('src.server.exist_application')
    @patch('src.server.add_app_to_webserver_routing')
    @patch('src.server.add_container_to_webserver_routing')
    def test_scale_application_if_it_is_already_running(
            self, mock_add_container, mock_add_app, mock_exist_application,
            mock_pick_up_node, mock_remove_app, mock_contact_nodes,
            mock_requests, mock_redis):
        conf = {
            'user': 'git',
            'repo': 'apache',
            'multiplicator': '2'
        }

        port = 4567
        node = self.nodes[0]
        mock_requests.get.return_value.status_code = 200
        mock_requests.get.return_value.content = json.dumps({'port': port})
        mock_pick_up_node.return_value = node
        response = self.c.get('/scale?multiplicator={}&user={}&repo={}'.format(
            conf.get('multiplicator'), conf.get('user'), conf.get('repo')))

        assert response.status_code == 200
        assert self.expected_conf(conf).get(
            'application_address') in response.data
        mock_contact_nodes.assert_called_once_with(self.expected_conf(conf))
        mock_remove_app.assert_called_once_with(
            mock_redis.StrictRedis(), self.expected_conf(conf))
        assert mock_pick_up_node.call_count == 2
        assert mock_exist_application.call_count == 3
        assert not mock_add_app.called

    @patch.dict('os.environ', {'DOOKIO_DOMAIN': 'localhost'})
    @patch('src.server.redis')
    @patch('src.server.requests')
    @patch('src.server.contact_nodes')
    @patch('src.server.remove_app_from_webserver_routing')
    @patch('src.server.pick_up_node')
    @patch('src.server.exist_application')
    @patch('src.server.add_app_to_webserver_routing')
    @patch('src.server.add_container_to_webserver_routing')
    def test_scale_application_when_a_node_returns_400(
            self, mock_add_container, mock_add_app, mock_exist_application,
            mock_pick_up_node, mock_remove_app, mock_contact_nodes,
            mock_requests, mock_redis):
        conf = {
            'user': 'git',
            'repo': 'apache',
            'multiplicator': '2'
        }

        node = self.nodes[0]
        mock_requests.get.return_value.status_code = 400
        mock_requests.get.return_value.content = 'Node unreachable'
        mock_pick_up_node.return_value = node
        response = self.c.get('/scale?multiplicator={}&user={}&repo={}'.format(
            conf.get('multiplicator'), conf.get('user'), conf.get('repo')))

        assert response.status_code == 400
        assert 'Node unreachable' in response.data
        mock_contact_nodes.assert_called_once_with(self.expected_conf(conf))
        mock_remove_app.assert_called_once_with(
            mock_redis.StrictRedis(), self.expected_conf(conf))
        assert mock_pick_up_node.call_count == 1
        assert mock_exist_application.call_count == 1
        assert not mock_add_app.called
        assert not mock_add_container.called

    @patch.dict('os.environ', {'DOOKIO_DOMAIN': 'localhost'})
    @patch('src.server.redis')
    def test_client_provides_an_unknown_path(self, mock_redis):
        conf = {
            'user': 'git',
            'repo': 'apache'
        }

        response = self.c.get('/unknown?user={}&repo={}'.format(
            conf.get('user'), conf.get('repo')))

        assert response.status_code == 200
        assert 'Something went wrong' in response.data

    @patch.dict('os.environ', {'DOOKIO_DOMAIN': 'localhost'})
    @patch('src.server.redis')
    @patch('src.server.contact_nodes')
    def test_client_provides_an_unknown_action(
            self, mock_contact_nodes, mock_redis):
        conf = {
            'action': 'unknown',
            'user': 'git',
            'repo': 'apache'
        }

        content = {
            node: []
            for node in self.nodes}

        response_nodes = {
            node: (content, 200)
            for node, content in content.iteritems()}

        mock_contact_nodes.return_value = response_nodes
        response = self.c.get('/containers?action={}&user={}&repo={}'.format(
            conf.get('action'), conf.get('user'), conf.get('repo')))

        expected_resp = [{
            'node': node_ip,
            'containers': body[0]
        } for node_ip, body in response_nodes.iteritems()]

        assert response.status_code == 200
        assert json.loads(response.data) == expected_resp
        mock_contact_nodes.assert_called_once_with(self.expected_conf(conf))
