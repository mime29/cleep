#!/usr/bin/env python
# -*- coding: utf-8 -*-
from gevent import monkey
monkey.patch_all()
from cleep.libs.internals.eventsbroker import EventsBroker
from cleep.libs.internals.profileformattersbroker import ProfileFormattersBroker
from cleep.libs.internals.cleepfilesystem import CleepFilesystem
from cleep.libs.internals.criticalresources import CriticalResources
from cleep.libs.internals.taskfactory import TaskFactory
from cleep.exception import NoResponse, CommandError
from cleep import bus
from cleep.libs.internals import event
import cleep.libs.internals.tools as tools
from cleep.common import ExecutionStep, MessageResponse
from cleep.libs.internals.drivers import Drivers
from threading import Event
import os
import logging
import types
import traceback
from unittest.mock import MagicMock
import re
import warnings

TRACE = tools.TRACE

class AnyArg(object):
    """
    Used to perform a "any" params comparison during an assert_called_with
    """
    def __eq__(a, b):
        return True

class PatternArg(object):
    """
    Used to perform a regexp param comparison during assert_called_with
    """
    def __init__(self, pattern):
        self.pattern = pattern

    def __eq__(self, b):
        return True if re.match(self.pattern, b) else False

    def __str__(self):
        return 'ContainArg(%s)' % self.pattern

class CommandFailure(object):
    """
    Used to reference a command failure in command mock response
    """
    def __init__(self, message=None):
        self.message = 'TEST: command failure' if message is None else message

class TestSession():
    """
    Create session to be able to run tests on a Cleep module
    """

    def __init__(self, testcase):
        """
        Constructor

        Args:
            testcase (unittest.TestCase): current unit test
        """
        tools.install_trace_logging_level()

        self.testcase = testcase
        self.__setup_executed = False
        self.__debug_enabled = False
        self.crash_report = None
        self.cleep_filesystem = None
        self.task_factory = None
        self.__module_class = None
        self.__bus_command_handlers = {}
        self.__event_handlers = {}
        self.__app_stop_event = None

    def __build_bootstrap_objects(self, debug):
        """
        Build bootstrap object with appropriate singleton instances
        All data is pre-configured for tests
        """
        self.crash_report = MagicMock()

        events_broker = EventsBroker(debug)
        events_broker.get_event_instance = self._events_broker_get_event_instance_mock

        internal_bus = bus.MessageBus(self.crash_report, debug)
        internal_bus.push = self._internal_bus_push_mock

        # enable writings during tests
        fs = CleepFilesystem()
        fs.enable_write(True, True)
        self.cleep_filesystem = MagicMock()
        
        core_join_event = Event()
        core_join_event.set()

        self.__app_stop_event = Event()
        # self.__app_stop_event.set()

        self.task_factory = TaskFactory({ 'app_stop_event': self.__app_stop_event })

        critical_resources = CriticalResources({ "task_factory": self.task_factory }, debug)

        return {
            'internal_bus': internal_bus,
            'events_broker': events_broker,
            'formatters_broker': EventsBroker(debug),
            'cleep_filesystem': self.cleep_filesystem,
            'crash_report': self.crash_report,
            'module_join_event': Event(),
            'core_join_event': core_join_event,
            'test_mode': True,
            'critical_resources': critical_resources,
            'execution_step': ExecutionStep(),
            'drivers': Drivers(debug),
            'log_file': '/tmp/cleep.log',
            'external_bus': 'cleepbus',
            'app_stop_event': self.__app_stop_event,
            'task_factory': self.task_factory,
        }

    def __get_test_case_name(self):
        """
        Return current test case name

        Returns:
            string: test case name
        """
        for item in traceback.extract_stack():
            if os.path.basename(item.filename).startswith('test_'):
                return item.name if item.name != '<module>' else '<test case name hidden by coverage>'
        return '<test case name not found>'

    def setup(self, module_class, bootstrap={}, clear_mocks=True, mock_on_start=True, mock_on_stop=True):
        """
        Instanciate specified module overwriting some stuff and initalizing it with appropriate content
        Can be called during test setup.

        Args:
            module_class (type): module class type
            bootstrap (dict): overwrite default bootstrap by specified one. You dont have to specify
                              all items, only specified ones will be replaced.
            clear_mocks (bool): True to clear all mocks. Useful for module respawn
            mock_on_start (bool): Mock _on_start method to avoid side effects during unit tests execution
            mock_on_stop (bool): Mock _on_stop method to avoid side effects during unit tests execution

        Returns:
            Object: returns module_class instance
        """
        warnings.simplefilter("ignore", ResourceWarning)

        # logger
        self.logger = logging.getLogger(self.__class__.__name__)
        self.__debug_enabled = True if logging.getLogger().getEffectiveLevel() <= logging.DEBUG else False
        self.test_case_name = self.__get_test_case_name()
        self.logger.debug('==> Running %s', self.testcase.id())
        
        # bootstrap object
        self.bootstrap = self.__build_bootstrap_objects(self.__debug_enabled)
        self.bootstrap.update(bootstrap)
        if clear_mocks:
            self.__bus_command_handlers.clear()
            self.__event_handlers.clear()
            self.__module_instance = None
        self.__module_class = module_class # used for respawn

        # config
        module_class.CONFIG_DIR = '/tmp'
        if not hasattr(module_class, 'MODULE_NAME'):
            setattr(module_class, 'MODULE_NAME', 'moduletest')
        
        # instanciate
        self.__module_instance = module_class(self.bootstrap, self.__debug_enabled)

        # mock some methods
        if mock_on_start:
            self.__module_instance._on_start = MagicMock()
        if mock_on_stop:
            self.__module_instance._on_stop = MagicMock()

        self.__setup_executed = True
        return self.__module_instance

    def start_module(self, module_instance):
        """
        Start module. Use this function if you disable module launch during setup

        Args:
            module_instance (instance): module instance returned by setup function
        """
        # start instance
        module_instance.start()

        # wait for module to be configured
        self.bootstrap['module_join_event'].wait()

        # wait for module to be really started
        module_instance._wait_is_started()
        self.logger.debug('===== module started =====')

    def respawn_module(self, start=True):
        """
        Respawn module instance (simulate module start)

        Args:
            start (bool): start module

        Returns:
            Object: returns module_class instance or None if setup not executed before
        """
        if not self.__setup_executed:
            return None

        # stop current running module instance
        self.__module_instance.stop()
        self.__module_instance.join()

        # create new module instance
        module_instance = self.setup(self.__module_class, self.bootstrap, False)

        # start instance
        if start:
            self.start_module(module_instance)

        return module_instance

    def clean(self):
        """
        Clean all session stuff.
        Can be called during test tear down.
        """
        if not self.__setup_executed:
            return

        # initiate Cleep shutdown
        self.__app_stop_event.set()

        # process
        if self.__module_instance and self.__module_instance.is_alive():
            self.__module_instance.stop()
            try:
                self.__module_instance.join(2.0)
            except RuntimeError as error:
                raise Exception('TEST: Please don\'t forget to start module application before running unit test (session.start_module())') from error

        # config
        if hasattr(self.__module_instance, 'MODULE_CONFIG_FILE'):
            path = os.path.join(self.__module_instance.CONFIG_DIR, self.__module_instance.MODULE_CONFIG_FILE)
            if os.path.exists(path):
                os.remove(path)

        if self.__module_instance:
            del self.__module_instance
            self.__module_instance = None

    def setup_event(self, event):
        """
        Return ready to use event

        Args:
            event (Class): event class to instanciate

        Returns:
            Event: event instance
        """
        # logger
        self.logger = logging.getLogger(self.__class__.__name__)
        self.__debug_enabled = True if logging.getLogger().getEffectiveLevel() <= logging.DEBUG else False
        self.test_case_name = self.__get_test_case_name()

        # bootstrap object
        self.bootstrap = self.__build_bootstrap_objects(self.__debug_enabled)

        return event({
            'internal_bus': self.bootstrap['internal_bus'],
            'formatters_broker': self.bootstrap['formatters_broker'],
            'external_bus_name': self.bootstrap['external_bus'],
            'get_external_bus_name': lambda: self.bootstrap['external_bus'],
        })

    def get_handled_commands(self):
        """
        Return list of handled commands
        
        Returns:
            list (string): list of commands
        """
        return list(self.__bus_command_handlers.keys())

    def make_mock_command(self, command_name, data=None, fail=False, no_response=False, side_effect=None):
        """
        Help user to make a ready to use command object

        Args:
            command_name (string): Command name
            data (any): Command response
            fail (bool): Set True to simulate command failure
            no_response (bool): Set True to simulate command no response
            side_effect (list): List of data to return. Each call to command returns first list item. If item if exception, it will be raised

        Returns:
            dict: awaited mocked command object
        """
        return {
            'command': command_name,
            'data': data,
            'fail': fail,
            'noresponse': no_response,
            'side_effect': side_effect,
        }

    def add_mock_command(self, command):
        """
        Mock command sent to internal message bus

        Args:
            command (dict): command object as returned by make_mock_command function
        """
        if not self.__setup_executed:
            raise Exception('TEST: Please run session.setup() before adding mocks')

        if command['command'] in self.__bus_command_handlers:
            self.logger.warning('Mock command "%s" already mocked' % command['command'])
            return

        self.__bus_command_handlers[command['command']] = {
            'data': command['data'],
            'side_effect': command['side_effect'],
            'calls': 0,
            'fail': command['fail'],
            'noresponse': command['noresponse'],
            'params': [],
            'last_to': None,
        }

    def set_mock_command_succeed(self, command_name):
        """
        Flag command as succeed will return specified data

        Args:
            command_name (string): command name
        """
        if command_name not in self.__bus_command_handlers:
            raise Exception(f'"{command_name}" not mocked. Please mock it first (session.add_mock_command)')

        self.__bus_command_handlers[command_name]['fail'] = False
        self.__bus_command_handlers[command_name]['noresponse'] = False

    def set_mock_command_fail(self, command_name):
        """
        Deprecated. Used only to keep test compatibility (typo in function name)

        Args:
            command_name (string): command name
        """
        self.set_mock_command_failed(command_name)

    def set_mock_command_failed(self, command_name):
        """
        When command is call a CommandError exception will be triggered

        Args:
            command_name (string): command name
        """
        if command_name not in self.__bus_command_handlers:
            raise Exception(f'"{command_name}" not mocked. Please mock it first (session.add_mock_command)')

        self.__bus_command_handlers[command_name]['fail'] = True
        self.__bus_command_handlers[command_name]['noresponse'] = False

    def set_mock_command_no_response(self, command_name):
        """
        When command is call a NoResponse exception will be triggered

        Args:
            command_name (string): command name
        """
        if command_name not in self.__bus_command_handlers:
            raise Exception(f'"{command_name}" not mocked. Please mock it first (session.add_mock_command)')

        self.__bus_command_handlers[command_name]['fail'] = False
        self.__bus_command_handlers[command_name]['noresponse'] = True

    def set_mock_command_response(self, command_name, data=None, side_effect=None):
        """
        Overwrite existing command response returned for next call
        
        Args:
            command_name (str): command name
            data (any): Command response
            side_effect (list): List of data to return. Each call to command returns first list item. If item if exception, it will be raised
        """
        if command_name not in self.__bus_command_handlers:
            raise Exception(f'"{command_name}" not mocked. Please mock it first (session.add_mock_command)')

        self.__bus_command_handlers[command_name]['fail'] = False
        self.__bus_command_handlers[command_name]['noresponse'] = False
        self.__bus_command_handlers[command_name]['data'] = data
        self.__bus_command_handlers[command_name]['side_effect'] = side_effect

    def set_mock_command_side_effects(self, command_name, side_effects):
        """

        """
        if command_name not in self.__bus_command_handlers:
            raise Exception(f'"{command_name}" not mocked. Please mock it first (session.add_mock_command)')

    def command_called(self, command_name):
        """
        Return True if command called

        Args:
            command_name (string): command name

        Returns:
            bool: True if command called, False otherwise
        """
        return True if self.command_call_count(command_name) else False

    def command_call_count(self, command_name):
        """
        Return how many times the command handler has been called

        Args:
            command_name (string): command name

        Returns:
            int: number of times handler has been called
        """
        if command_name in self.__bus_command_handlers:
            return self.__bus_command_handlers[command_name]['calls']

        return 0

    def __check_command_called_with_params(self, command, params):
        """
        Check among all stored command parameters if specified ones have been called with

        Args:
            command (dict): command object
            params (dict): command parameters to check

        Returns:
            bool: True if command was called with specified parameters, False otherwise
        """
        for cmd_params in command['params']:
            if cmd_params == params:
                return True
        return False

    def command_called_with(self, command_name, params, to=None):
        """
        Return True if command is called with specified parameters

        Args:
            command_name (string): command name
            params (dict): command parameters
            to (string): command recipient. If to is specified, the value is used to check command validity

        Returns:
            bool: True if command called with params
        """
        if command_name in self.__bus_command_handlers:
            params_check = self.__check_command_called_with_params(self.__bus_command_handlers[command_name], params)
            params_error = ('  Expected params: %s\n  Received params: %s' % (params, self.__bus_command_handlers[command_name]['params'])
                            if not params_check else '')
            to_check = True if to is None else self.__bus_command_handlers[command_name]['lastto'] == to
            to_error = ('  Expected to: %s\n  Current to: %s' % (to, self.__bus_command_handlers[command_name]['lastto'])
                        if not to_check else '')

            check = params_check and to_check
            if not check:
                self.logger.fatal('TEST: command_called_with failed:\n%s%s%s' % (params_error, ('\n' if params_error else ''), to_error))
            return check

        self.logger.fatal(
            'TEST: command_called_with failed: command not mocked in "%s", please mock it using session.add_mock_command' % self.test_case_name
        )
        return False

    def assert_command_not_called(self, command_name):
        """
        Assert command was not called
        """
        # check command is registered
        if command_name not in self.__bus_command_handlers:
            self.testcase.fail('Command mock "%s" was not registered' % command_name)

        # check command was called
        if self.__bus_command_handlers[command_name]['calls'] != 0:
            self.testcase.fail('Command "%s" was called while it should not' % command_name)

    def assert_command_called(self, command_name, to=None):
        """
        Assert command was called
        Like command_called_with but with assertion
        """
        # check command is registered
        if command_name not in self.__bus_command_handlers:
            self.testcase.fail('Command mock "%s" was not registered' % command_name)

        # check command was called
        if self.__bus_command_handlers[command_name]['calls'] == 0:
            self.testcase.fail('Command "%s" was not called' % command_name)

        # check command recipient
        if to is not None:
            self.testcase.assertEqual(
                self.__bus_command_handlers[command_name]['lastto'],
                to,
                'Command "%s" recipient is different' % command_name,
            )

    def assert_command_called_with(self, command_name, params, to=None):
        """
        Same as command_called_with but with assertion
        """
        # check command is registered
        if command_name not in self.__bus_command_handlers:
            self.testcase.fail('Command mock "%s" was not registered' % command_name)

        # check command was called
        if self.__bus_command_handlers[command_name]['calls'] == 0:
            self.testcase.fail('Command "%s" was not called' % command_name)

        # check command params
        if len(self.__bus_command_handlers[command_name]['params']) == 1:
            if type(params) is not type(self.__bus_command_handlers[command_name]['params'][0]):
                self.testcase.fail('Command "%s" parameters differs: %s is not %s (%s)' % (
                    command_name,
                    type(params).__name__,
                    type(self.__bus_command_handlers[command_name]['params'][0]).__name__,
                    self.__bus_command_handlers[command_name]['params'][0],
                ))
            elif isinstance(params, dict):
                self.testcase.assertDictEqual(
                    self.__bus_command_handlers[command_name]['params'][0],
                    params,
                    'Command "%s" parameters are differents' % command_name,
                )
            elif params is None:
                self.testcase.assertIsNone(
                    self.__bus_command_handlers[command_name]['params'][0],
                    'Command "%s" parameters are not None' % command_name,
                )
        else:
            params_check = self.__check_command_called_with_params(self.__bus_command_handlers[command_name], params)
            if not params_check:
                self.testcase.fail('Command "%s" was not called with awaited parameters\n  Expected params: %s\n  Received params: %s' % (
                    command_name,
                    params,
                    self.__bus_command_handlers[command_name]['params'],
                ))

        # check command recipient
        if to is not None:
            self.testcase.assertEqual(
                self.__bus_command_handlers[command_name]['lastto'],
                to,
                'Command "%s" recipient is different' % command_name,
            )

    def event_called(self, event_name):
        """
        Return True if event has been called

        Args:
            event_name (string): event name

        Returns:
            bool: True if event called
        """
        return True if self.event_call_count(event_name) > 0 else False

    def assert_event_not_called(self, event_name):
        """
        Assert specified event was not called
        """
        self.testcase.assertTrue(self.event_call_count(event_name) == 0, 'Event "%s" was called while it should' % event_name)

    def assert_event_called(self, event_name):
        """
        Same as event_called with assertion
        """
        self.testcase.assertTrue(self.event_call_count(event_name) > 0, 'Event "%s" was not called while it should' % event_name)

    def event_call_count(self, event_name):
        """
        Returns event calls count

        Returns:
            int: number of event calls count or 0 if event not handled
        """
        if event_name in self.__event_handlers:
            return self.__event_handlers[event_name]['sends']

        return 0

    def event_called_with(self, event_name, params):
        """
        Return True if event has been called with specified arguments

        Args:
            event_name (string): event name
            params (dict): dict of parameters

        Returns:
            bool: True if event called with params
        """
        last_params = self.get_last_event_params(event_name)
        check = True if params == last_params else False
        if not check:
            self.logger.fatal('TEST: event_called_with failed:\n  Expected: %s\n  Current:  %s' % (params, last_params))
        return check

    def assert_event_called_with(self, event_name, params, device_id=None):
        """
        Assert event called with

        Args:
            event_name (string): event name
            params (dict): event parameters
            device_id (string): device id
        """
        self.testcase.assertTrue(self.event_call_count(event_name) > 0, 'Event "%s" was not called' % event_name)
        last_params = self.get_last_event_params(event_name)
        self.testcase.assertDictEqual(params, last_params, 'Event "%s" parameters are differents' % event_name)
        if device_id is not None:
            last_deviceid = self.get_last_event_device_id(event_name)
            self.testcase.assertEqual(device_id, last_deviceid)

    def get_last_event_params(self, event_name):
        """
        Returns event params of last call

        Returns:
            dict: last event call params or None if event not handled
        """
        if event_name in self.__event_handlers:
            return self.__event_handlers[event_name]['lastparams']

        return None

    def get_last_event_device_id(self, event_name):
        """
        Returns event device_id of last call

        Returns:
            string: last event call device_id
        """
        if event_name in self.__event_handlers:
            return self.__event_handlers[event_name]['lastdeviceid']

        return None

    def _internal_bus_push_mock(self, request, timeout):
        """
        Mocked internal bus push method
        """
        self.logger.debug('TEST: Process command %s' % request)
        if request and request.command in self.__bus_command_handlers:
            self.logger.debug('TEST: push command "%s"' % request.command)
            self.__bus_command_handlers[request.command]['calls'] += 1
            self.__bus_command_handlers[request.command]['params'].append(request.params)
            self.__bus_command_handlers[request.command]['lastdeviceid'] = request.device_id
            self.__bus_command_handlers[request.command]['lastto'] = request.to

            if self.__bus_command_handlers[request.command]['fail']:
                self.logger.debug('TEST: command "%s" fails for tests' % request.command)
                raise CommandError('TEST: command "%s" fails for tests' % request.command)
            elif self.__bus_command_handlers[request.command]['noresponse']:
                self.logger.debug('TEST: command "%s" returns no response for tests' % request.command)
                raise NoResponse(request.to, request.timeout, 'TEST: no response for command "%s"' % request.command)

            cmd_data = self.__bus_command_handlers[request.command]['data']
            cmd_side_effect = self.__bus_command_handlers[request.command]['side_effect']
            if cmd_data is None and cmd_side_effect is None:
                data = cmd_data
            elif isinstance(cmd_side_effect, list):
                if len(cmd_side_effect) > 0:
                    data = cmd_side_effect.pop(0)
                    if isinstance(data, Exception):
                        self.logger.debug('TEST: command "%s" fails for tests with custom "%s" exception', request.command, data.__class__.__name__)
                        raise data
                    elif isinstance(data, CommandFailure):
                        self.logger.debug('TEST: command "%s" fails for test', request.command)
                        return MessageResponse(
                            error=True,
                            data=None,
                            message=data.message,
                        )
                else:
                    self.logger.warning(
                        'TEST: command "%s" is called more often than it has mocked responses. Return None by default.',
                        request.command
                    )
                    data = None
            else:
                 data = cmd_data

            return MessageResponse(
                error=False,
                data=data,
                message='',
            )

        self.logger.fatal(
            'TEST: Command "%s" is not handled in "%s", please mock it using session.add_mock_command.' % (
                request.command,
                self.test_case_name
            )
        )
        raise Exception(
            'TEST: command "%s" is not handled in "%s", please mock it using session.add_mock_command' % (
                request.command,
                self.test_case_name
            )
        )

    def _events_broker_get_event_instance_mock(self, event_name):
        """
        Create monkey-patched Event of specified name
        """
        e_ = event.Event
        e_.EVENT_NAME = event_name
        instance = e_({
            'internal_bus': self.bootstrap['internal_bus'],
            'formatters_broker': self.bootstrap['formatters_broker'],
            'get_external_bus_name': 'testexternalbus',
        })
        self.__event_handlers[event_name] = {
            'sends': 0,
            'lastparams': None,
            'lastdeviceid': None,
        }
        event_handlers = self.__event_handlers
        # monkey patch new event send() method
        def event_send_mock(self, params=None, device_id=None, to=None, render=True):
            self.logger.debug('TEST: send event "%s"' % event_name)
            event_handlers[event_name]['sends'] += 1
            event_handlers[event_name]['lastparams'] = params
            event_handlers[event_name]['lastdeviceid'] = device_id
        instance.send = types.MethodType(event_send_mock, instance)

        return instance

    @staticmethod
    def clone_class(base_class):
        """
        Clone specified base class. This can be useful when you need to alter class (adding mock)
        keeping original one clean.

        Args:
            base_class (Class): class object (not instance!)

        Returns:
            Class: cloned class that can be instanciated. Cloned class name is prefixed by "C"
        """
        class ClonedClass(base_class):
            pass
        ClonedClass.__name__ = 'C%s' % base_class.__name__

        return ClonedClass

