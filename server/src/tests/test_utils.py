import unittest
import json
from mock import patch, Mock

from src.utils import (pick_up_node,
                       fetch_apps,
                       contact_containers,
                       contact_nodes,
                       add_app_to_webserver_routing,
                       remove_app_from_webserver_routing,
                       exist_application,
                       add_container_to_webserver_routing,
                       was_applied)


class ServerUtilsTestSuite(unittest.TestCase):
    def setUp(self):
        self.nodes = ['http://0.0.0.0', 'http://123.123.123.123']

    @patch('src.utils.get_nodes')
    def test_that_nodes_are_picked_properly(self, mock_get_nodes):
        mock_get_nodes.return_value = self.nodes
        node = pick_up_node()

        assert mock_get_nodes.called
        assert node in self.nodes

    def test_that_apps_are_fetch_from_redis(self):
        redis_apps = ['1', '2']

        redis_cli = Mock()
        redis_cli.scan_iter.return_value = redis_apps
        redis_cli.lrange.return_value = True
        apps = fetch_apps(redis_cli)

        assert len(apps) == 2
        for a in redis_apps:
            assert apps[a] is True

    @patch('src.utils.requests.get')
    def test_that_containers_are_being_contacted(self, mock_requests):
        action = 'stop'
        node = 'http://0.0.0.0'
        user = 'git'
        repo = 'apache'

        contact_containers(action, node, user, repo)
        assert mock_requests.called
        mock_requests.assert_called_once_with(
            '{}:5000/containers?action={}&user={}&repo={}'.format(
                node, action, user, repo))

    @patch('src.utils.contact_containers')
    @patch('src.utils.get_nodes')
    def test_that_contact_nodes_with_200_response(
            self, mock_get_nodes, mock_contact_containers):
        conf = {
            'action': 'stop',
            'user': 'git',
            'repo': 'apache'
        }
        expected_content = {
            node: {
                'node': node
            } for node in self.nodes}

        expected_response = {
            node: (content, 200)
            for node, content in expected_content.iteritems()}

        def side_effect(action, node, user, repo):
            mock = Mock()
            mock.status_code = 200
            mock.content = json.dumps(expected_content[node])
            return mock
        mock_get_nodes.return_value = self.nodes
        mock_contact_containers.side_effect = side_effect

        response = contact_nodes(conf)

        assert response == expected_response
        assert mock_get_nodes.called
        assert mock_contact_containers.call_count == len(self.nodes)

    @patch('src.utils.contact_containers')
    @patch('src.utils.get_nodes')
    def test_that_contact_nodes_with_400_response(
            self, mock_get_nodes, mock_contact_containers):
        conf = {
            'action': 'stop',
            'user': 'git',
            'repo': 'apache'
        }
        expected_content = {
            node: 'Container not accessible'
            for node in self.nodes}

        expected_response = {
            node: (content, 400)
            for node, content in expected_content.iteritems()}

        def side_effect(action, node, user, repo):
            mock = Mock()
            mock.status_code = 400
            mock.content = expected_content[node]
            return mock
        mock_get_nodes.return_value = self.nodes
        mock_contact_containers.side_effect = side_effect

        response = contact_nodes(conf)
        assert response == expected_response
        assert mock_get_nodes.called
        assert mock_contact_containers.call_count == len(self.nodes)

    def test_add_app_to_webserver_routing(self):
        redis_cli = Mock()
        conf = {
            'repo': 'apache',
            'application_address': 'git.apache.example.com'
        }
        add_app_to_webserver_routing(redis_cli, conf)

        redis_cli.rpush.assert_called_once_with('frontend:{}'.format(
            conf.get('application_address')), conf.get('repo'))

    def test_remove_app_from_webserver_routing(self):
        redis_cli = Mock()
        conf = {
            'application_address': 'git.apache.example.com'
        }
        remove_app_from_webserver_routing(redis_cli, conf)

        redis_cli.delete.assert_called_once_with(
            'frontend:{}'.format(conf.get('application_address')))

    def test_exists_application(self):
        redis_cli = Mock()
        redis_cli.lrange.return_value = True
        conf = {
            'application_address': 'git.apache.example.com'
        }
        response = exist_application(redis_cli, conf)
        assert response is True

        redis_cli.lrange.assert_called_once_with(
            'frontend:{}'.format(conf.get('application_address')), 0, -1)

    def test_add_container_to_webserver_routing(self):
        redis_cli = Mock()
        conf = {
            'application_address': 'git.apache.example.com'
        }
        node = self.nodes[0]
        port = 4678
        add_container_to_webserver_routing(redis_cli, node, port, conf)

        redis_cli.rpush.assert_called_once_with(
            'frontend:{}'.format(
                conf.get('application_address')), '{}:{}'.format(node, port))

    def test_was_applied_when_zero_nodes_were_affected(self):
        content = {
            node: {
                'node': node
            } for node in self.nodes}

        response_nodes = {
            node: (content, 400)
            for node, content in content.iteritems()}

        response = was_applied(response_nodes)

        assert response is False

    def test_was_applied_when_some_nodes_were_affected(self):
        content = {
            node: {
                'node': node
            } for node in self.nodes}

        response_nodes = {
            node: (content, 200)
            for node, content in content.iteritems()}

        response = was_applied(response_nodes)

        assert response is True
