#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.tests.lib import TestLib
import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests', ''))
import rpcserver
from cleep.libs.drivers.driver import Driver
from cleep.common import MessageRequest, MessageResponse
from cleep.exception import NoMessageAvailable
import unittest
import logging
from boddle import boddle
from bottle import HTTPError, HTTPResponse
from unittest.mock import Mock, patch, mock_open, ANY
import json
import time
from collections import OrderedDict
from cleep.libs.tests.common import get_log_level

LOG_LEVEL = get_log_level()

class DummyDriver(Driver):
    def __init__(self, processing=False, is_installed=False, is_installed_exception=False):
        self.__processing = processing
        self.__is_installed = is_installed
        self.__is_installed_exception = is_installed_exception
    def processing(self):
        return self.__processing
    def is_installed(self):
        if self.__is_installed_exception:
            raise Exception('Test exception')
        return self.__is_installed

class RpcServerTests(unittest.TestCase):

    DRIVERS = {
        'audio': {
            'driver1': DummyDriver(True, False),
            'driver2': DummyDriver(False, True)
        },
        'gpio': {
        }
    }
    RENDERERS = {
        'module1': ['profile1'],
        'module2' : ['profile1', 'profile2']
    }
    EVENTS = {
        'event1': {
            'modules': ['module1', 'module2'],
            'profiles': ['profile1', 'profile2']
        },
        'event2': {
            'modules': [],
            'profiles': ['profile3']
        }
    }
    MODULES = {
        'module1': {
            'name': 'module1',
            'version': '0.0.0'
        },
        'module2': {
            'name': 'module2',
            'version': '0.0.0'
        },
    }
    MODULES_CONFIGS = {
        'module1': {
            'key1': 'vale1',
        },
        'module2': {
            'key2': 'value2',
        },
    }
    DEVICES = {
        'module1': {
            '123-456-789': {
                'name': 'device1'
            },
            '987-645-321': {
                'name': 'device2'
            },
        },
        'module2': {
            '456-789-312': {
                'name': 'device3'
            }
        }
    }

    def setUp(self):
        TestLib()
        logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

    def tearDown(self):
        if rpcserver:
            rpcserver.sessions.clear()
            if isinstance(rpcserver.CLEEP_CACHE, dict):
                rpcserver.CLEEP_CACHE.clear()
            #if rpcserver.logger:
            #    rpcserver.logger.setLevel(logging.getLogger().getEffectiveLevel())

    def _init_context(self, push_return_value=None, push_side_effect=None, no_bus=False, is_subscribed_return_value=None, is_subscribed_side_effect=None,
            pull_return_value=None, pull_side_effect=None, get_drivers_side_effect=None, get_drivers_gpio_exception=False, debug_enabled=False,
            host='0.0.0.0', port=80, ssl_key=None, ssl_cert=None, exec_configure=True):
        self.crash_report = Mock()
        self.cleep_filesystem = Mock()
        self.internal_bus = Mock()
        if push_return_value is not None:
            self.internal_bus.push.return_value = push_return_value
        if push_side_effect is not None:
            self.internal_bus.push.side_effect = push_side_effect
        if pull_return_value is not None:
            self.internal_bus.pull.return_value = pull_return_value
        if pull_side_effect is not None:
            self.internal_bus.pull.side_effect = pull_side_effect
        if is_subscribed_return_value is not None:
            self.internal_bus.is_subscribed.return_value = is_subscribed_return_value
        if is_subscribed_side_effect is not None:
            self.internal_bus.is_subscribed.side_effect = is_subscribed_side_effect
        self.bootstrap = {
            'internal_bus': None if no_bus else self.internal_bus,
            'cleep_filesystem': self.cleep_filesystem,
            'crash_report': self.crash_report,
        }

        self.inventory = Mock()
        self.inventory.get_renderers.return_value = self.RENDERERS
        if get_drivers_side_effect is None:
            self.inventory.get_drivers.return_value = self.DRIVERS
            if get_drivers_gpio_exception:
                self.inventory.get_drivers.return_value['gpio']['driverfailed'] = DummyDriver(is_installed_exception=True)
        else:
            self.inventory.get_drivers.side_effect = get_drivers_side_effect
        self.inventory.get_used_events.return_value = self.EVENTS
        self.inventory.get_modules.return_value = self.MODULES
        self.inventory.get_installable_modules.return_value = self.MODULES
        self.inventory.get_devices.return_value = self.DEVICES
        self.inventory.get_modules_configs.return_value = self.MODULES_CONFIGS

        rpc_config = {
            'host': host,
            'port': port,
            'ssl': True if ssl_key and ssl_cert else False,
            'ssl_key': ssl_key,
            'ssl_cert': ssl_cert,
        }

        if exec_configure:
            rpcserver.configure(rpc_config, self.bootstrap, self.inventory, debug_enabled)

    @patch('rpcserver.CleepConf')
    def test_load_auth_with_no_accounts_and_enabled(self, cleep_conf_mock):
        cleep_conf_mock.return_value.is_auth_enabled.return_value = True
        cleep_conf_mock.return_value.get_auth_accounts.return_value = {}
        self._init_context()

        with boddle():
            self.assertFalse(rpcserver.auth_enabled)

    @patch('rpcserver.CleepConf')
    def test_load_auth_with_accounts_and_disabled(self, cleep_conf_mock):
        cleep_conf_mock.return_value.is_auth_enabled.return_value = False
        cleep_conf_mock.return_value.get_auth_accounts.return_value = {
            'test': '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08'
        }
        self._init_context()

        with boddle():
            self.assertFalse(rpcserver.auth_enabled)

    @patch('rpcserver.CleepConf')
    def test_load_auth_with_accounts_and_enabled(self, cleep_conf_mock):
        cleep_conf_mock.return_value.is_auth_enabled.return_value = True
        cleep_conf_mock.return_value.get_auth_accounts.return_value = {
            'test': '$5$rounds=535000$VeU5e79jNXnS3b4z$atnocFYx/vEmrv2KAiFvofeHLPu3ztVF0uI5SLUMuo2'
        }
        self._init_context()

        with boddle():
            self.assertTrue(rpcserver.auth_enabled)
            self.assertEqual(len(rpcserver.auth_accounts), 1)
            self.assertTrue('test' in rpcserver.auth_accounts)

    @patch("rpcserver.CleepConf")
    @patch("rpcserver.logging")
    def test_load_auth_failed(self, logging_mock, cleep_conf_mock):
        cleep_conf_mock.return_value.is_auth_enabled.side_effect = Exception('Test exception')
        logger_mock = Mock()
        logging_mock.getLogger = Mock(return_value=logger_mock)
        self._init_context()
        
        with boddle():
            # self.assertTrue(self.crash_report.report_exception.called)
            rpcserver.logger.exception.assert_called_with("Unable to load auth file. Auth disabled:")

    @patch("rpcserver.CleepConf")
    def test_check_auth(self, cleep_conf_mock):
        cleep_conf_mock.return_value.is_auth_enabled.return_value = True
        cleep_conf_mock.return_value.get_auth_accounts.return_value = {
            'test': '$5$rounds=535000$VeU5e79jNXnS3b4z$atnocFYx/vEmrv2KAiFvofeHLPu3ztVF0uI5SLUMuo2'
        }
        self._init_context()

        with boddle():
            self.assertEqual(len(rpcserver.sessions.keys()), 0)
            self.assertTrue(rpcserver.check_auth('test', 'test'))
            self.assertEqual(len(rpcserver.sessions.keys()), 1)
            logging.debug('Sessions: %s' % type(rpcserver.sessions.keys()))
            session_key = list(rpcserver.sessions.keys())[0]
            old_time = rpcserver.sessions[session_key]

            # check it uses sessions
            time.sleep(1.0)
            self.assertTrue(rpcserver.check_auth('test', 'test'))
            new_time = rpcserver.sessions[session_key]
            self.assertNotEqual(new_time, old_time)

    @patch("rpcserver.CleepConf")
    def test_check_auth_bad_password(self, cleep_conf_mock):
        cleep_conf_mock.return_value.is_auth_enabled.return_value = True
        cleep_conf_mock.return_value.get_auth_accounts.return_value = {
            'test': '$5$rounds=535000$tLWAIhyEYBj9JX8D$QqkTEqm9dpfz2.Fnu.C1QryHkav6lYu56/PbTb7sD3/'
        }
        self._init_context()

        with boddle():
            self.assertFalse(rpcserver.check_auth('test', 'test'))

    @patch('rpcserver.CleepConf')
    def test_check_auth_invalid_password(self, cleep_conf_mock):
        cleep_conf_mock.return_value.is_auth_enabled.return_value = True
        cleep_conf_mock.return_value.get_auth_accounts.return_value = {
            'test': 'Hkav6lYu56/PbTb7sD3/'
        }
        self._init_context()

        with boddle():
            self.assertFalse(rpcserver.check_auth('test', 'test'))

    @patch('rpcserver.CleepConf')
    def test_check_auth_invalid_user(self, cleep_conf_mock):
        cleep_conf_mock.return_value.is_auth_enabled.return_value = True
        cleep_conf_mock.return_value.get_auth_accounts.return_value = {
            'test': '$5$rounds=535000$tLWAIhyEYBj9JX8D$QqkTEqm9dpfz2.Fnu.C1QryHkav6lYu56/PbTb7sD3/'
        }
        self._init_context()

        with boddle():
            self.assertFalse(rpcserver.check_auth('dummy', 'test'))

    def test_start(self):
        self._init_context()

        with patch('rpcserver.server') as mock_server:
            rpcserver.start()

            self.assertTrue(mock_server.serve_forever.called)
            mock_server.close.assert_called()
            mock_server.stop.assert_called()

    def test_start_already_started(self):
        self._init_context()

        with patch('rpcserver.server') as mock_server:
            mock_server.serve_forever.side_effect = OSError()
            with patch('rpcserver.logger.fatal') as mock_logger_fatal:
                rpcserver.start()

                mock_logger_fatal.assert_called_with('Cleep instance is already running')
                mock_server.close.assert_called()
                mock_server.stop.assert_called()
                self.crash_report.report_exception.assert_not_called()

    def test_start_ctrl_c(self):
        self._init_context()

        with patch('rpcserver.server') as mock_server:
            mock_server.serve_forever.side_effect = KeyboardInterrupt()
            rpcserver.start()

            mock_server.close.assert_called()
            mock_server.stop.assert_called()
            self.crash_report.report_exception.assert_not_called()

    def test_start_exception(self):
        self._init_context()

        with patch('rpcserver.server') as mock_server:
            mock_server.serve_forever.side_effect = Exception('Test error')
            with patch('rpcserver.logger.exception') as mock_logger_exception:
                rpcserver.start()

                mock_logger_exception.assert_called()
                mock_server.close.assert_called()
                mock_server.stop.assert_called()
                self.crash_report.report_exception.assert_called()

    def test_set_cache_control(self):
        self._init_context()

        with boddle():
            rpcserver.set_cache_control(True)
            self.assertTrue(rpcserver.cache_enabled)

            rpcserver.set_cache_control(False)
            self.assertFalse(rpcserver.cache_enabled)

    def test_set_debug(self):
        self._init_context()

        with boddle():
            rpcserver.set_debug(True)
            self.assertEqual(rpcserver.debug_enabled, True)
            self.assertEqual(rpcserver.logger.getEffectiveLevel(), logging.DEBUG)
            self.assertTrue(rpcserver.is_debug_enabled())

            rpcserver.set_debug(False)
            self.assertEqual(rpcserver.debug_enabled, False)
            self.assertEqual(rpcserver.logger.getEffectiveLevel(), logging.getLogger().getEffectiveLevel())
            self.assertFalse(rpcserver.is_debug_enabled())

    @patch('rpcserver.pywsgi.WSGIServer')
    def test_configure(self, mock_wsgi):
        self._init_context(exec_configure=False)
        rpc_config = {
            'host': '1.2.3.4',
            'port': 123,
        }

        rpcserver.configure(rpc_config, self.bootstrap, self.inventory, False)

        mock_wsgi.assert_called_with(('1.2.3.4', 123), ANY, error_log=ANY, log=ANY, spawn=ANY)

    @patch('rpcserver.pywsgi.WSGIServer')
    def test_configure_with_default_config(self, mock_wsgi):
        self._init_context(exec_configure=False)

        rpcserver.configure({}, self.bootstrap, self.inventory, False)

        mock_wsgi.assert_called_with(('0.0.0.0', 80), ANY, error_log=ANY, log=ANY, spawn=ANY)

    @patch('rpcserver.pywsgi.WSGIServer')
    def test_configure_with_valid_ssl(self, mock_wsgi):
        self._init_context(exec_configure=False)
        rpc_config = {
            'host': '1.2.3.4',
            'port': 123,
            'ssl': True,
            'ssl_key': 'mykey',
            'ssl_cert': 'mycert',
        }

        rpcserver.configure(rpc_config, self.bootstrap, self.inventory, False)

        mock_wsgi.assert_called_with(('1.2.3.4', 123), ANY, error_log=ANY, log=ANY, spawn=ANY, keyfile='mykey', certfile='mycert', do_handshake_on_connect=False)

    @patch('rpcserver.pywsgi.WSGIServer')
    def test_configure_with_invalid_ssl(self, mock_wsgi):
        self._init_context(exec_configure=False)
        rpc_config = {
            'host': '1.2.3.4',
            'port': 123,
            'ssl': False,
            'ssl_key': 'mykey',
            'ssl_cert': 'mycert',
        }

        rpcserver.configure(rpc_config, self.bootstrap, self.inventory, False)

        mock_wsgi.assert_called_with(('1.2.3.4', 123), ANY, error_log=ANY, log=ANY, spawn=ANY)

    @patch("rpcserver.logging")
    def test_configure_debug_enabled(self, logging_mock):
        logger_mock = Mock()
        logging_mock.getLogger.return_value = logger_mock
        self._init_context(debug_enabled=True)

        with boddle():
            self.assertEqual(rpcserver.debug_enabled, True)
            self.assertTrue(rpcserver.is_debug_enabled())
            logger_mock.setLevel.assert_called()

    def test_configure_debug_disabled(self):
        self._init_context(debug_enabled=False)

        with boddle():
            self.assertEqual(rpcserver.debug_enabled, False)
            self.assertEqual(rpcserver.logger.getEffectiveLevel(), logging.getLogger().getEffectiveLevel())
            self.assertFalse(rpcserver.is_debug_enabled())

    def test_send_command(self):
        self._init_context()

        with boddle():
            # with timeout
            r = rpcserver.send_command(command='cmd', to='module', params={}, timeout=3.0)
            self.assertTrue(self.internal_bus.push.called_once)
            args = self.internal_bus.push.call_args
            logging.debug('Args: %s' % str(args))
            self.assertTrue(isinstance(args[0][0], MessageRequest))
            self.assertEqual(len(args[0]), 2)
            self.assertEqual(args[0][1], 3.0)

            # without timeout
            r = rpcserver.send_command(command='cmd', to='module', params={})
            self.assertTrue(self.internal_bus.push.called_once)
            args = self.internal_bus.push.call_args
            logging.debug('Args: %s' % str(args))
            self.assertTrue(isinstance(args[0][0], MessageRequest))
            self.assertEqual(len(args[0]), 1)


    def test_get_events(self):
        self._init_context()

        with boddle():
            e = rpcserver.get_events()
            logging.debug('Events: %s' % e)
            self.assertEqual(e, {
                'error': False,
                'message': '',
                'data': self.EVENTS
            })

    def test_get_commands(self):
        self._init_context()
        rpcserver.configure({}, self.bootstrap, self.inventory, False)
        commands = {"module1": ["command1"], "module2": ["command2", "command3"]}
        self.inventory.get_module_commands.return_value = commands

        with boddle():
            c = rpcserver.get_commands()
            logging.debug("Commands: %s", c)
            self.assertEqual(c, {
                'error': False,
                'message': '',
                'data': commands,
            })

    def test_check_app_documentation_with_valid_doc(self):
        self._init_context()
        rpcserver.configure({}, self.bootstrap, self.inventory, False)
        self.inventory.check_module_documentation.return_value = {"command": { "valid": True}}

        with boddle():
            resp = rpcserver.check_app_documentation("app")
            logging.debug("Resp: %s", resp)
            self.assertDictEqual(resp, {
                'error': False,
                'message': '',
                'data': {'command': {'valid': True}}
            })

    def test_check_app_documentation_with_exception(self):
        self._init_context()
        rpcserver.configure({}, self.bootstrap, self.inventory, False)
        self.inventory.check_module_documentation.side_effect = Exception("Error")

        with boddle():
            resp = rpcserver.check_app_documentation("app")
            logging.debug("Resp: %s", resp)

            self.assertDictEqual(resp, {
                'error': True,
                'message': "Error",
                'data': None
            })

    def test_check_app_documentation_with_invalid_doc(self):
        self._init_context()
        rpcserver.configure({}, self.bootstrap, self.inventory, False)
        self.inventory.check_module_documentation.return_value = {"command": { "valid": False}}

        with boddle():
            resp = rpcserver.check_app_documentation("app")
            logging.debug("Resp: %s", resp)
            self.assertDictEqual(resp, {
                'error': True,
                'message': 'Invalid application documentation',
                'data': {'command': {'valid': False}}
            })

    def test_get_app_documentation(self):
        self._init_context()
        rpcserver.configure({}, self.bootstrap, self.inventory, False)
        self.inventory.get_module_documentation.return_value = "documentation"

        with boddle():
            resp = rpcserver.get_app_documentation("app")
            logging.debug("Resp: %s", resp)
            self.assertDictEqual(resp, {
                'error': False,
                'message': '',
                'data': 'documentation'
            })

    def test_get_app_documentation_with_exception(self):
        self._init_context()
        rpcserver.configure({}, self.bootstrap, self.inventory, False)
        self.inventory.get_module_documentation.side_effect = Exception("Error")

        with boddle():
            resp = rpcserver.get_app_documentation("app")
            logging.debug("Resp: %s", resp)
            self.assertDictEqual(resp, {
                'error': True,
                'message': 'Error',
                'data': None
            })

    def test_modules(self):
        self._init_context()

        with boddle():
            m = rpcserver.get_modules()
            logging.debug('Modules: %s' % m)
            self.assertEqual(m, {
                'error': False,
                'message': '',
                'data': self.MODULES
            })
            self.assertFalse(self.inventory.get_installable_modules.called)
            self.assertTrue(self.inventory.get_modules.called)

    def test_modules_with_installable_true(self):
        self._init_context()

        with boddle(json={'installable': True}):
            m = rpcserver.get_modules()
            logging.debug('Modules: %s' % m)
            self.assertEqual(m, {
                'error': False,
                'message': '',
                'data': self.MODULES,
                })
            self.assertTrue(self.inventory.get_installable_modules.called)
            self.assertFalse(self.inventory.get_modules.called)

    def test_modules_with_installable_false(self):
        self._init_context()

        with boddle(json={'installable': False}):
            m = rpcserver.get_modules()
            logging.debug('Modules: %s' % m)
            self.assertEqual(m, {
                'error': False,
                'message': '',
                'data': self.MODULES
            })
            self.assertFalse(self.inventory.get_installable_modules.called)
            self.assertTrue(self.inventory.get_modules.called)

    def test_devices(self):
        self._init_context()

        with boddle(method='POST'):
            resp = rpcserver.get_devices()
            self.assertEqual(resp, {
                'error': False,
                'message': '',
                'data': self.DEVICES
            })

    def test_renderers(self):
        self._init_context()

        with boddle(method='POST'):
            r = rpcserver.get_renderers()
            self.assertEqual(r, {
                'error': False,
                'message': '',
                'data': self.RENDERERS
            })

    def test_drivers(self):
        self._init_context()
        a1 = OrderedDict({
            "drivertype": "audio",
            "processing": True,
            "drivername": "driver1",
            "installed": False,
        })
        a2 = OrderedDict({
            "drivertype": "audio",
            "processing": False,
            "drivername": "driver2",
            "installed": True,
        })
        with boddle(method='POST'):
            resp = rpcserver.get_drivers()
            logging.debug('Resp: %s' % resp)
            self.assertEqual(len(resp['data']), 2)
            self.assertTrue(resp['data'][0] in [a1, a2])
            self.assertTrue(resp['data'][1] in [a1, a2])

    def test_drivers_one_driver_exception(self):
        self._init_context(get_drivers_gpio_exception=True)

        with boddle(method='POST'):
            resp = rpcserver.get_drivers()
            logging.debug('Resp: %s' % resp)
            self.assertEqual(len(resp['data']), 2)

    @patch("rpcserver.CleepConf")
    def test_reload_auth(self, cleep_conf_mock):
        is_auth_enabled_mock = Mock(return_value=True)
        cleep_conf_mock.return_value.is_auth_enabled = is_auth_enabled_mock
        cleep_conf_mock.return_value.get_auth_accounts.return_value = {
            'test': '$5$rounds=535000$tLWAIhyEYBj9JX8D$QqkTEqm9dpfz2.Fnu.C1QryHkav6lYu56/PbTb7sD3/'
        }
        self._init_context(get_drivers_gpio_exception=True)

        rpcserver.reload_auth()

        self.assertEqual(is_auth_enabled_mock.call_count, 2)

    @patch('rpcserver.bottle')
    def test_upload(self, mock_bottle):
        mock_bottle.request = Mock()
        mock_bottle.request.forms = {
            'command': 'upload_command',
            'to': 'dummymodule',
            'params': None,
        }
        mock_fileupload = Mock(filename='myfilename')
        mock_bottle.request.files = {
            'file': mock_fileupload,
        }
        original_sendcommand = rpcserver.send_command
        rpcserver.send_command = Mock()
        self._init_context()

        try:
            resp = rpcserver.exec_upload()

            mock_fileupload.save.assert_called_with('/tmp/myfilename')
            rpcserver.send_command.assert_called_with('upload_command', 'dummymodule', {'filepath': '/tmp/myfilename'}, 10.0)
        finally:
            rpcserver.send_command = original_sendcommand

    @patch('rpcserver.bottle')
    def test_upload_with_params(self, mock_bottle):
        mock_bottle.request = Mock()
        mock_bottle.request.forms = {
            'command': 'upload_command',
            'to': 'dummymodule',
            'params': {'key': 'value'},
        }
        mock_fileupload = Mock(filename='myfilename')
        mock_bottle.request.files = {
            'file': mock_fileupload,
        }
        original_sendcommand = rpcserver.send_command
        rpcserver.send_command = Mock()
        self._init_context()

        try:
            resp = rpcserver.exec_upload()

            mock_fileupload.save.assert_called_with('/tmp/myfilename')
            rpcserver.send_command.assert_called_with('upload_command', 'dummymodule', {'filepath': '/tmp/myfilename', 'key': 'value'}, 10.0)
        finally:
            rpcserver.send_command = original_sendcommand

    def test_upload_missing_params(self):
        self._init_context()

        with boddle():
            r = rpcserver.exec_upload()
            logging.debug('Response: %s' % r)
            self.assertEqual(r, {'message': 'Missing parameters', 'data': None, 'error': True})

    @patch('rpcserver.bottle')
    @patch('rpcserver.os.path.exists')
    @patch('rpcserver.os.remove')
    def test_upload_file_already_exists(self, mock_osremove, mock_ospathexists, mock_bottle):
        mock_ospathexists.return_value = True
        mock_bottle.request = Mock()
        mock_bottle.request.forms = {
            'command': 'upload_command',
            'to': 'dummymodule',
            'params': None,
        }
        mock_fileupload = Mock(filename='myfilename')
        mock_fileupload.save.side_effect = Exception('Test exception')
        mock_bottle.request.files = {
            'file': mock_fileupload,
        }
        original_sendcommand = rpcserver.send_command
        rpcserver.send_command = Mock()
        self._init_context()

        try:
            resp = rpcserver.exec_upload()

            mock_osremove.assert_called_with('/tmp/myfilename')
        finally:
            rpcserver.send_command = original_sendcommand

    @patch('rpcserver.bottle')
    @patch('rpcserver.os.remove')
    def test_upload_missing_parameters(self, mock_osremove, mock_bottle):
        mock_bottle.request = Mock()
        mock_bottle.request.forms = {
            'to': 'dummymodule',
            'params': None,
        }
        original_sendcommand = rpcserver.send_command
        rpcserver.send_command = Mock()
        self._init_context()

        try:
            resp = rpcserver.exec_upload()

            self.assertEqual(resp['error'], True)
            self.assertEqual(resp['message'], 'Missing parameters')
            mock_osremove.assert_not_called()
        finally:
            rpcserver.send_command = original_sendcommand

    @patch('rpcserver.bottle')
    @patch('rpcserver.os.path.exists')
    @patch('rpcserver.os.remove')
    def test_upload_exception_with_file_deletion(self, mock_osremove, mock_ospathexists, mock_bottle):
        mock_ospathexists.return_value = True
        mock_bottle.request = Mock()
        mock_bottle.request.forms = {
            'command': 'upload_command',
            'to': 'dummymodule',
            'params': None,
        }
        mock_fileupload = Mock(filename='myfilename')
        mock_fileupload.save.side_effect = Exception('Test exception')
        mock_bottle.request.files = {
            'file': mock_fileupload,
        }
        original_sendcommand = rpcserver.send_command
        rpcserver.send_command = Mock()
        self._init_context()

        try:
            resp = rpcserver.exec_upload()
            logging.debug('Resp: %s', resp)

            self.assertEqual(resp['error'], True)
            self.assertEqual(resp['message'], 'Test exception')
            mock_osremove.assert_called_with('/tmp/myfilename')
        finally:
            rpcserver.send_command = original_sendcommand

    def test_download_wo_params(self):
        message = MessageResponse(error=False, data={'filepath':'/tmp/123456789', 'filename':'dummy.test'}, message=None)
        self._init_context(push_return_value=message)

        with boddle(query={'command':'cmd', 'to':'dummy'}):
            resp = rpcserver.exec_download()
            logging.debug('Response: %s' % resp)
            args = self.internal_bus.push.call_args
            self.assertTrue(isinstance(args[0][0], MessageRequest))
            logging.debug('MessageRequest: %s' % args[0][0].to_dict())
            self.assertEqual(args[0][0].to_dict(), {'broadcast': False, 'params': {}, 'command': 'cmd', 'sender': 'rpcserver', 'to': 'dummy'})

    def test_download_w_params(self):
        message = MessageResponse(error=False, data={'filepath':'/tmp/123456789', 'filename':'dummy.test'}, message=None)
        self._init_context(push_return_value=message)

        with boddle(query={'command':'cmd', 'to':'dummy', 'params': {'dummy': 'value'}}):
            resp = rpcserver.exec_download()
            logging.debug('Response: %s' % resp)
            args = self.internal_bus.push.call_args
            self.assertTrue(isinstance(args[0][0], MessageRequest))
            logging.debug('MessageRequest: %s' % args[0][0].to_dict())
            self.assertEqual(args[0][0].to_dict(), {'broadcast': False, 'params': {'params': "{'dummy': 'value'}"}, 'command': 'cmd', 'sender': 'rpcserver', 'to': 'dummy'})

    def test_download_failed(self):
        self._init_context(push_return_value=MessageResponse(error=True, data=None, message='Command failed'))

        with boddle(query={'command':'cmd', 'to':'dummy', 'params': {'dummy': 'value'}}):
            resp = rpcserver.exec_download()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, {'message': 'Command failed', 'data': None, 'error': True})

    def test_download_exception(self):
        self._init_context(push_side_effect=Exception('Test exception'))

        with boddle(query={'command':'cmd', 'to':'dummy'}):
            resp = rpcserver.exec_download()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, {'message': 'Test exception', 'data': None, 'error': True})

    def test_command_get(self):
        return_value = MessageResponse(error=False, data={'key':'value'}, message=None)
        self._init_context(push_return_value=return_value)

        with boddle(method='GET', query={'command':'cmd', 'to':'dummy', 'params':json.dumps({'p1':'v1'}), 'timeout':3.0}):
            resp = rpcserver.exec_command()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, return_value.to_dict())
            args = self.internal_bus.push.call_args
            logging.debug(args[0][0])
            self.assertEqual(args[0][0].params, {'p1':'v1'})
            self.assertEqual(args[0][0].sender, 'rpcserver')

    def test_command_get_params_in_query(self):
        return_value = MessageResponse(error=False, data={'key':'value'}, message=None)
        self._init_context(push_return_value=return_value)

        with boddle(method='GET', query={'command':'cmd', 'to':'dummy', 'p1':'v1'}):
            resp = rpcserver.exec_command()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, return_value.to_dict())
            args = self.internal_bus.push.call_args
            logging.debug(args[0][0])
            self.assertEqual(args[0][0].params, {'p1':'v1'})

    def test_command_get_failed(self):
        return_value = MessageResponse(error=True, data=None, message='Command failed')
        self._init_context(push_return_value=return_value)

        with boddle(method='GET', query={'command':'cmd', 'to':'dummy', 'params':{'p1':'v1'}}):
            resp = rpcserver.exec_command()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, return_value.to_dict())

    def test_command_get_exception(self):
        self._init_context(push_side_effect=Exception('Test exception'))

        with boddle(method='GET', query={'command':'cmd', 'to':'dummy', 'params':{'p1':'v1'}}):
            resp = rpcserver.exec_command()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, {'message': 'Test exception', 'data': None, 'error': True})

    def test_command_post(self):
        return_value = MessageResponse(error=False, data={'key':'value'}, message=None)
        self._init_context(push_return_value=return_value)

        with boddle(method='POST', json={'command':'cmd', 'to':'dummy', 'params':{'p1':'v1'}, 'timeout':3.0}):
            resp = rpcserver.exec_command()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, return_value.to_dict())
            args = self.internal_bus.push.call_args
            logging.debug(args[0][0])
            self.assertEqual(args[0][0].params, {'p1':'v1'})
            self.assertEqual(args[0][0].sender, 'rpcserver')

    def test_command_post_no_params(self):
        return_value = MessageResponse(error=False, data={'key':'value'}, message=None)
        self._init_context(push_return_value=return_value)

        with boddle(method='POST', json={'command':'cmd', 'to':'dummy'}):
            resp = rpcserver.exec_command()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, return_value.to_dict())
            args = self.internal_bus.push.call_args
            logging.debug(args[0][0])
            self.assertEqual(args[0][0].sender, 'rpcserver')

    def test_command_post_not_json(self):
        return_value = MessageResponse(error=False, data={'key':'value'}, message=None)
        self._init_context(push_return_value=return_value)

        with boddle(method='POST', query={'command':'cmd', 'to':'dummy', 'params':{'p1':'v1'}}):
            resp = rpcserver.exec_command()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, {'message': 'Invalid payload, json required.', 'data': None, 'error': True})

    def test_command_post_failed(self):
        return_value = MessageResponse(error=True, data=None, message='Command failed')
        self._init_context(push_return_value=return_value)

        with boddle(method='POST', json={'command':'cmd', 'to':'dummy', 'params':{'p1':'v1'}}):
            resp = rpcserver.exec_command()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, return_value.to_dict())

    def test_command_post_exception(self):
        self._init_context(push_side_effect=Exception('Test exception'))

        with boddle(method='POST', json={'command':'cmd', 'to':'dummy', 'params':{'p1':'v1'}}):
            resp = rpcserver.exec_command()
            logging.debug('Response: %s' % resp)
            self.assertEqual(resp, {'message': 'Test exception', 'data': None, 'error': True})

    def test_config(self):
        self._init_context()

        with boddle():
            resp = rpcserver.get_config()
            logging.debug('Resp: %s' % resp)
            config = resp['data']
            self.assertTrue('modules' in config)
            for module_name, module in config['modules'].items():
                self.assertTrue('config' in module)
            self.assertTrue('events' in config)
            self.assertTrue('renderers' in config)
            self.assertTrue('devices' in config)
            self.assertTrue('drivers' in config)
            self.assertIsNotNone(config['modules'])
            self.assertIsNotNone(config['events'])
            self.assertIsNotNone(config['renderers'])
            self.assertIsNotNone(config['devices'])
            self.assertIsNotNone(config['drivers'])

            self.assertEqual(self.inventory.get_modules.call_count, 1)

    @patch('json.dumps')
    def test_config_exception(self, json_dumps_mock):
        self._init_context()
        # keep original function to restore it after test execution (there is only one rpcserver instance)
        get_devices_from_inventory = rpcserver.get_devices_from_inventory

        try:
            rpcserver.get_devices_from_inventory = Mock(side_effect=Exception('Test exception'))

            with boddle():
                resp = rpcserver.get_config()
                logging.debug('Resp: %s' % resp)
                self.assertIsNone(resp['data'])
        finally:
            rpcserver.get_devices_from_inventory = get_devices_from_inventory

    def test_config_use_cache(self):
        self._init_context()

        with boddle():
            rpcserver.get_config()
            rpcserver.get_config()
            self.assertEqual(self.inventory.get_modules.call_count, 1)

    def test_get_remote_access_urls(self):
        self._init_context()

        with boddle():
            rpcserver.get_remote_access_urls()
            self.assertTrue(self.inventory.get_remote_access_urls.called)

    def test_registerpoll(self):
        self._init_context()

        with boddle():
            resp = json.loads(rpcserver.registerpoll())
            logging.debug('Resp: %s' % resp)
            self.assertTrue('pollKey' in resp)
            self.assertIsNotNone(resp['pollKey'])
            self.assertTrue(self.internal_bus.add_subscription.called_once)

    def test_poll_no_pollkey(self):
        self._init_context()

        with boddle(json={}):
            resp = rpcserver.poll()
            logging.debug('Resp: %s' % resp)
            self.assertEqual(resp, {'message': 'Polling key is missing', 'data': None, 'error': True})

    def test_poll_no_bus(self):
        self._init_context(no_bus=True)

        with boddle(json={}):
            resp = rpcserver.poll()
            logging.debug('Resp: %s' % resp)
            self.assertEqual(resp, {'message': 'Bus not available', 'data': None, 'error': True})

    def test_poll_not_registered(self):
        self._init_context(is_subscribed_return_value=False)

        with boddle(json={'pollKey': '123-456-789'}):
            resp = rpcserver.poll()
            logging.debug('Resp: %s' % resp)
            self.assertEqual(resp, {'message': 'Client not registered', 'data': None, 'error': True})

    def test_poll(self):
        pull_resp = {
            'message': 'hello world'
        }
        self._init_context(pull_return_value=pull_resp)

        with boddle(json={'pollKey': '123-456-789'}):
            resp = rpcserver.poll()
            logging.debug('Poll response: %s', resp)
            logging.debug('Resp: %s' % resp)
            self.assertEqual(resp['data'], pull_resp['message'])
            self.assertEqual(resp['message'], '')

    def test_poll_no_message_available(self):
        pull_resp = {
            'message': 'hello world'
        }
        self._init_context(pull_side_effect=NoMessageAvailable())

        with boddle(json={'pollKey': '123-456-789'}):
            resp = rpcserver.poll()
            logging.debug('Resp: %s' % resp)
            self.assertEqual(resp['data'], None)
            self.assertEqual(resp['message'], 'No message available')

    def test_poll_exception(self):
        pull_resp = {
            'message': 'hello world'
        }
        self._init_context(pull_side_effect=Exception('Test exception'))

        with boddle(json={'pollKey': '123-456-789'}):
            resp = rpcserver.poll()
            logging.debug('Resp: %s' % resp)
            self.assertEqual(resp['data'], None)
            self.assertEqual(resp['message'], 'Internal error')

    def test_rpc_wrapper(self):
        self._init_context()

        with boddle(query={'p1':'v1', 'p2':'v2'}):
            rpcserver.rpc_wrapper('')
            self.assertTrue(self.inventory.rpc_wrapper.called)

    def test_default(self):
        self._init_context()

        with boddle():
            d = rpcserver.default('index.html')
            logging.debug('Default: %s' % type(d))
            self.assertTrue(isinstance(d, HTTPResponse))
            logging.debug('%s' % d.status)
            self.assertEqual(d.status, '200 OK')

    def test_index(self):
        self._init_context()

        with boddle():
            i = rpcserver.index()
            logging.debug('Index: %s' % type(i))
            self.assertTrue(isinstance(i, HTTPResponse))
            logging.debug('%s' % i.status)
            self.assertEqual(i.status, '200 OK')

    def test_logs(self):
        self._init_context()
        message = 'cleep log file content'
        self.cleep_filesystem.read_data.return_value = message

        with boddle():
            resp = rpcserver.logs()
            logging.debug('Resp: %s' % resp)
            self.assertTrue(message in resp)

        self.cleep_filesystem.read_data.assert_called_with('/var/log/cleep.log')

    def test_authenticate(self):
        self._init_context()
        
        auth_enabled_restore = rpcserver.auth_enabled
        try:
            with boddle():
                rpcserver.auth_enabled = True
                c = rpcserver.get_config()
                logging.debug('Config: %s' % type(c))
                self.assertTrue(isinstance(c, HTTPError))
                logging.debug('%s' % c.status)
                self.assertEqual(c.status, '401 Unauthorized')

        finally:
            rpcserver.auth_enabled = auth_enabled_restore
            



if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_rpcserver.py; coverage report -m -i
    unittest.main()

