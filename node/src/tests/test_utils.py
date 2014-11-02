import unittest
from mock import patch, Mock

from src.utils import (_reserve_container,
                       start_container,
                       stop_containers,
                       get_containers,
                       create_image,
                       remove_image,
                       create_container)


class NodeUtilsTestSuite(unittest.TestCase):
    def setUp(self):
        self.port = 4567
        self.cli = Mock()
        self.conf = {
            'user': 'git',
            'repo': 'portfolio',
            'local_path': '/tmp'
        }
        self.container_name = "/{}_{}_{}".format(self.conf.get('user'), self.conf.get('repo'), self.port)
        self.tag = "{}/{}".format(self.conf.get('user'), self.conf.get('repo'))

    @patch('src.utils.get_port')
    @patch('src.utils.make_port_available')
    def test_that_the_container_is_reserved(self,
                                            mock_make_port_available,
                                            mock_get_port):
        expected_container = {
            'Id': 'sdffdfdsfsfds'
        }
        mock_get_port.return_value = self.port
        self.cli.create_container.return_value = expected_container
        container, port = _reserve_container(self.cli, self.conf)

        assert mock_get_port.called
        assert self.cli.create_container.called
        self.cli.create_container.assert_called_once_with(name=self.container_name[1:], image=self.tag, command="", ports=[80])
        self.cli.start.assert_called_once_with(container=expected_container.get('Id'), port_bindings={80: self.port})
        assert not mock_make_port_available.called
        assert container is expected_container
        assert port == 4567

    @patch('src.utils._reserve_container')
    def test_create_container_if_success(self,
            mock_reserve_container):
        expected_container = {
            'Id': 'sdffdfdsfsfds'
        }
        mock_reserve_container.return_value = expected_container, self.port

        container, port = create_container(self.cli, self.conf)

        mock_reserve_container.assert_called_once_with(self.cli, self.conf)
        assert container is expected_container
        assert port is self.port

    @patch('src.utils._reserve_container')
    def test_create_container_if_exception(self,
            mock_reserve_container):

        mock_reserve_container.side_effect = Exception()

        self.assertRaises(Exception, create_container, (self.cli, self.conf))

    @patch('src.utils.get_containers')
    @patch('src.utils._reserve_container')
    def test_start_container_if_app_is_not_running(self,
            mock_reserve_container, mock_get_containers):
        expected_container = {
            'Id': 'sdffdfdsfsfds'
        }
        mock_reserve_container.return_value = expected_container, self.port
        mock_get_containers.side_effect = [[], [expected_container]]

        containers = start_container(self.cli, self.conf)

        mock_reserve_container.assert_called_once_with(self.cli, self.conf)
        assert mock_get_containers.call_count == 2
        assert containers == [expected_container]

    @patch('src.utils.get_containers')
    @patch('src.utils._reserve_container')
    def test_start_container_if_app_is_running(self,
            mock_reserve_container, mock_get_containers):
        expected_container = {
            'Id': 'sdffdfdsfsfds'
        }
        mock_reserve_container.return_value = expected_container, self.port
        mock_get_containers.return_value = [expected_container]
        self.assertRaises(Exception, start_container, (self.cli, self.conf))
        assert not mock_reserve_container.called

    @patch('src.utils.get_containers')
    @patch('src.utils._reserve_container')
    def test_start_container_if_app_does_not_exist(self,
            mock_reserve_container, mock_get_containers):
        mock_reserve_container.side_effect = Exception('Application does not exist')
        mock_get_containers.return_value = []
        self.assertRaises(Exception, start_container, (self.cli, self.conf))

    @patch('src.utils.make_port_available')
    def test_stop_container_if_one_container_is_running(self,
            mock_make_port_available):
        expected_container = {
            "Names": [self.container_name],
            "Ports": [{"PublicPort": self.port}],
            "Id": "qwerty12345"
        }

        self.cli.containers.return_value = [expected_container]
        stop_containers(self.cli, self.conf)
        mock_make_port_available.assert_called_once_with(
            expected_container.get("Ports")[0].get("PublicPort"))
        assert self.cli.kill.called
        self.cli.remove_container.assert_called_once_with(
            expected_container.get("Id"), force=True)

    @patch('src.utils.make_port_available')
    def test_stop_container_if_several_containers_are_running(self,
            mock_make_port_available):
        expected_container = {
            "Names": [self.container_name],
            "Ports": [{"PublicPort": self.port}],
            "Id": "qwerty12345"
        }

        self.cli.containers.return_value = [expected_container, expected_container]
        stop_containers(self.cli, self.conf)
        assert mock_make_port_available.call_count == 2
        mock_make_port_available.assert_called_with(
            expected_container.get("Ports")[0].get("PublicPort"))
        assert self.cli.kill.call_count == 2
        assert self.cli.remove_container.call_count == 2
        self.cli.remove_container.assert_called_with(
            expected_container.get("Id"), force=True)

    @patch('src.utils.make_port_available')
    def test_stop_container_if_no_containers_are_running(self,
            mock_make_port_available):

        self.cli.containers.return_value = []
        self.assertRaises(Exception, stop_containers, (self.cli, self.conf))
        assert not mock_make_port_available.called
        assert not self.cli.kill.called
        assert not self.cli.remove_container.called

    def test_get_containers(self):
        expected_container = {
            "Names": [self.container_name],
            "Ports": [{"PublicPort": self.port}],
            "Id": "qwerty12345"
        }

        self.cli.containers.return_value = [expected_container]

        containers = get_containers(self.cli, self.conf)
        assert expected_container in containers

    def test_get_containers_if_there_are_other_apps_deployed(self):
        expected_container = {
            "Names": [self.container_name],
            "Ports": [{"PublicPort": self.port}],
            "Id": "qwerty12345"
        }

        another_app_container = {
            "Names": ["/git_apache_4568"],
            "Ports": [{"PublicPort": 4568}],
            "Id": "qwerty12345"
        }

        self.cli.containers.return_value = [expected_container, another_app_container]

        containers = get_containers(self.cli, self.conf)
        assert expected_container in containers
        assert len(containers) == 1

    def test_create_image(self):
        local_path = self.conf.get('local_path')
        instructions = (x for x in range(10))
        self.cli.build.return_value = instructions
        containers = create_image(self.cli, self.conf)

        assert containers == instructions
        self.cli.build.assert_called_once_with(path=local_path, tag=self.tag)

    def test_remove_image(self):
        expected_image = {
            "RepoTags": [self.tag],
            "Id": "qwerty12345"
        }
        self.cli.images.return_value = [expected_image]

        remove_image(self.cli, self.conf)

        self.cli.remove_image.assert_called_once_with(expected_image.get('Id'), force=True)

    def test_remove_image_if_it_does_not_exist_for_that_app(self):
        another_image = {
            "RepoTags": ["git/apache"],
            "Id": "qwerty12345"
        }

        self.cli.images.return_value = [another_image]

        remove_image(self.cli, self.conf)

        assert not self.cli.remove_image.called
