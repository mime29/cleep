#!/usr/bin/env python
# -*- coding: utf-8 -*-
    
import os
import logging
import importlib
import inspect
import copy
from threading import Event, Timer
import sys
from types import ModuleType, FunctionType
from gc import get_referents
from cleep.core import Cleep, CleepModule, CleepRenderer, CleepRpcWrapper
from cleep.libs.configs.appssources import AppsSources
from cleep.exception import CommandError, MissingParameter, InvalidParameter
from cleep.libs.internals.install import Install
import cleep.libs.internals.tools as Tools
from cleep.common import CORE_MODULES, ExecutionStep
from cleep.libs.internals.task import Task
from cleep import __version__ as CLEEP_VERSION

__all__ = ['Inventory']

class Inventory(Cleep):
    """
    Inventory handles inventory of:
     - existing devices: knows all devices and module that handles it
     - loaded modules and their commands
     - existing renderers (sms, email, sound...)
    """

    MODULE_AUTHOR = 'Cleep'
    MODULE_VERSION = '0.0.0'
    MODULE_CORE = True
    MODULE_NAME = 'inventory'

    MODULES_SYNC_TIMEOUT = 60.0
    PYTHON_CLEEP_IMPORT_PATH = 'cleep.modules.'
    PYTHON_CLEEP_MODULES_PATH = 'modules'

    def __init__(self, bootstrap, rpcserver, debug_enabled, configured_modules, debug_config):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects
            rpcserver (Bottle): rpcserver instance (used to set debug)
            debug_enabled (bool): debug inventory or not
            configured_modules (list): list of configured modules to start::

                ['module1', 'module2', ...]

            debug_config (dict): debug computed from config and command line::

                {
                    trace_enabled (bool): trace enabled flag
                    debug_modules (list): list of modules to enable debug
                }

        """
        # init
        Cleep.__init__(self, bootstrap, debug_enabled)
        # self.logger.setLevel(logging.DEBUG)

        # members
        self.CLEEP_ENV = os.environ.get("CLEEP_ENV", "").lower()
        self.__modules_loaded = False
        self.__rpcserver = rpcserver
        self.configured_modules = configured_modules
        self.debug_config = debug_config
        self.bootstrap = bootstrap
        self.events_broker = bootstrap['events_broker']
        self.formatters_broker = bootstrap['formatters_broker']
        self.task_factory = bootstrap["task_factory"]
        # dict to store event to synchronize module startups
        self.__module_join_events = []
        # used to store modules status (library or not) during modules loading
        self.__modules_loaded_as_dependency = {}
        # list of modules: dict(<module name>:dict(<module config>), ...)
        self.modules = {}
        # direct access to modules instances
        self.__modules_instances = {}
        # modules that failed to starts
        # format::
        #   {
        #       module name (string): error (string),
        #       ...
        #   }
        self.__modules_in_error = {}
        # module names that are CleepRpcWrapper instances
        self.__rpc_wrappers = []
        # modules dependencies
        self.__dependencies = {}
        # current module loading tree
        self.__module_loading_tree = []
        self.__remote_access_urls = {}

        # events
        self.apps_updated_event = self._get_event('core.apps.updated')

    def _configure(self):
        """
        Configure module
        """
        self._load_modules()

        if os.getenv('MEMORY_MONITORING'): # pragma: no cover
            self.logger.info('Starting memory monitoring task')
            self.__memory_monitoring_task = Task(21600, self.__memory_monitoring, self.logger)
            self.__memory_monitoring_task.start()

    def __get_bootstrap(self):
        """
        Get a copy of bootstrap object to pass to module to load
        This function instanciate a new Event for module synchronization and pass all other attributes
        """
        bootstrap = copy.copy(self.bootstrap)
        bootstrap['module_join_event'] = Event()

        return bootstrap

    def __fix_country(self, country):
        return '' if not country else country.lower()

    def __fix_urls(self, site_url, bugs_url, info_url, help_url):
        return {
            'site': site_url,
            'bugs': bugs_url,
            'info': info_url,
            'help': help_url
        }

    def __load_module(self, module_name, local_modules, is_dependency=False):
        """
        Load specified module

        Args:
            module_name (string): module name
            local_modules (list): list of locally installed modules
            is_dependency (bool): True if module to load is a dependency (default: False)
        """
        if is_dependency:
            self.logger.debug('Loading dependency "%s"', module_name)
        else:
            self.logger.debug('Loading application "%s"', module_name)

        # handle circular dependency
        if module_name in self.__module_loading_tree:
            self.logger.warning('Circular dependency detected')
            return
        self.__module_loading_tree.append(module_name)
        self.logger.trace('Application tree: %s', self.__module_loading_tree)

        # handle already loaded dependency
        if module_name in self.__modules_loaded_as_dependency:
            self.logger.trace('Loading dependency "%s" as an app after it has been loaded as dependency', module_name)
            self.__modules_loaded_as_dependency[module_name] = False
            return

        # set module is installed
        if module_name not in self.modules and module_name not in local_modules:
            raise Exception('Application "%s" doesn\'t exist. Parent app and app dependencies won\'t be loaded.' % module_name)
        self.modules[module_name]['installed'] = True

        # import module file and get module class
        module_path = '%s%s' % (self.PYTHON_CLEEP_IMPORT_PATH, module_name)
        module_ = importlib.import_module(module_path)
        app_filename = getattr(module_, 'APP_FILENAME', module_name)
        del module_
        class_path = '%s%s.%s' % (self.PYTHON_CLEEP_IMPORT_PATH, module_name, app_filename)
        self.logger.trace('Importing application "%s"', class_path)
        module_ = importlib.import_module(class_path)
        module_class_ = getattr(module_, app_filename.capitalize())
        setattr(module_class_, 'MODULE_NAME', module_name)
                    
        # enable or not debug
        debug = False
        if self.debug_config['trace_enabled'] or module_name in self.debug_config['debug_modules']:
            self.logger.debug('Debug enabled for application "%s"', module_name)
            debug = True

        # load module dependencies
        self.logger.trace('Application "%s" dependencies: %s', module_name, module_class_.MODULE_DEPS)
        if module_class_.MODULE_DEPS:
            for dependency in module_class_.MODULE_DEPS:
                self.logger.trace('Processing "%s" application dependency "%s"', module_name, dependency)
                # update dependencies list
                if dependency not in self.__dependencies:
                    self.__dependencies[dependency] = []
                self.__dependencies[dependency].append(module_name)
                self.logger.trace('Dependencies list: %s', self.__dependencies)
                
                if dependency not in self.__modules_instances:
                    # load dependency
                    self.logger.trace('Load dependency "%s"', dependency)
                    self.__load_module(dependency, local_modules, is_dependency=True)
                    self.__module_loading_tree.pop()

                    # flag module is loaded as dependency and not module
                    self.__modules_loaded_as_dependency[dependency] = True
            
                else:
                    # dependency is already loaded, nothing else to do
                    self.logger.trace('Dependency "%s" already loaded', dependency)

        # is module external bus implementation
        if 'CleepExternalBus' in [c.__name__ for c in module_class_.__bases__]:
            self.bootstrap['external_bus'] = module_name

        # instanciate module
        self.logger.trace('Instanciating application "%s"', module_name)
        bootstrap = self.__get_bootstrap()
        self.__modules_instances[module_name] = module_class_(bootstrap, debug)

        # append module join event to make sure all modules are loaded
        self.__module_join_events.append(bootstrap['module_join_event'])

        # fix some metadata
        fixed_urls = self.__fix_urls(
            getattr(module_class_, 'MODULE_URLSITE', None),
            getattr(module_class_, 'MODULE_URLBUGS', None),
            getattr(module_class_, 'MODULE_URLINFO', None),
            getattr(module_class_, 'MODULE_URLHELP', None)
        )
        fixed_country = self.__fix_country(getattr(module_class_, 'MODULE_COUNTRY', None))

        # update metadata with module values
        self.modules[module_name].update({
            'label': getattr(module_class_, 'MODULE_LABEL', module_name.capitalize()),
            'description': module_class_.MODULE_DESCRIPTION,
            'author': getattr(module_class_, 'MODULE_AUTHOR', ''),
            'core': module_name in CORE_MODULES,
            'tags': getattr(module_class_, 'MODULE_TAGS', []),
            'country': fixed_country,
            'urls': fixed_urls,
            'category': getattr(module_class_, 'MODULE_CATEGORY', ''),
            'screenshots': getattr(module_class_, 'MODULE_SCREENSHOTS', []),
            'deps': getattr(module_class_, 'MODULE_DEPS', []),
            'version': getattr(module_class_, 'MODULE_VERSION', '0.0.0'),
        })

        # flag module is loaded as module and not dependency
        self.__modules_loaded_as_dependency[module_name] = False

    def _get_market(self):
        """
        Get content of market

        Returns:
            dict: market content::

            {
                update (int): last update timestamp
                list (dict): list of applications
            }

        """
        apps_sources = AppsSources(self.cleep_filesystem, self.task_factory)
        market = apps_sources.get_market()
        return market

    def reload_modules(self):
        """
        Reload modules refreshing only not installed modules
        """
        self.logger.info('Reloading modules')
        # get list of all available modules (from remote list)
        modules_json_content = self._get_market()
        modules_json = modules_json_content['list']
        self.logger.trace('modules.json: %s', modules_json)

        # iterates over new modules.json
        for module_name, module_data in modules_json.items():
            if module_name not in self.modules:
                # new module, add new entry in existing modules list
                self.logger.debug('Add new application "%s" to list of available applications', module_name)
                self.modules[module_name] = module_data
                
                # add/force some metadata
                self.modules[module_name].update({
                    'name': module_name,
                    'installed': False,
                    'library': False,
                    'local': False,
                    'core': False,
                    'screenshots': [],
                    'deps': [],
                    'loadedby': [],
                })

        # trigger modules update event
        self.apps_updated_event.send()

    def _load_modules(self):
        """
        Load all modules
        """
        # init
        if self.__modules_loaded:
            raise Exception('Modules loading must be performed only once. If you want to refresh modules list, use reload_modules instead')
        local_modules = []
                
        # get list of all available modules (from remote list)
        modules_json_content = self._get_market()
        self.modules = modules_json_content['list']
        self.logger.trace('Modules.json: %s', self.modules)

        # append manually installed modules (surely app in development)
        local_modules_path = os.path.abspath(os.path.join(os.path.dirname(__file__), self.PYTHON_CLEEP_MODULES_PATH))
        self.logger.debug('Local modules path: %s', local_modules_path)
        if not os.path.exists(local_modules_path): # pragma: no cover
            raise CommandError('Invalid modules path')
        for f in os.listdir(local_modules_path):
            fpath = os.path.join(local_modules_path, f)
            module_name = os.path.split(fpath)[-1]
            if module_name.startswith('__'):
                continue
            module_path = '%s%s' % (self.PYTHON_CLEEP_IMPORT_PATH, module_name)
            module_ = importlib.import_module(module_path)
            app_filename = getattr(module_, 'APP_FILENAME', module_name)
            module_py = os.path.join(fpath, '%s.py' % app_filename)
            if os.path.isdir(fpath) and os.path.exists(module_py) and module_name not in self.modules:
                self.logger.debug('Found application "%s" installed manually', module_name)
                local_modules.append(module_name)
                self.modules[module_name] = {}
        self.logger.debug('Local applications: %s', local_modules)

        # add default metadata
        for module_name, module in self.modules.items():
            module.update({
                'name': module_name,
                'installed': False,
                'library': False,
                'local': module_name in local_modules,
                'core': False,
                'screenshots': [],
                'deps': [],
                'loadedby': [],
                'version': module.get('version', '0.0.0'),
            })

        # execution step: BOOT->INIT
        self.bootstrap['execution_step'].step = ExecutionStep.INIT

        # load core modules
        self.logger.trace('CORE_MODULES: %s', CORE_MODULES)
        for module_name in CORE_MODULES:
            try:
                # load module
                self.__load_module(module_name, local_modules)

            except Exception as error:
                # failed to load mandatory module
                self.__modules_in_error[module_name] = str(error)
                if self.CLEEP_ENV != 'ci':
                    self.logger.exception('Core application "%s" exception:', module_name)
                    self.logger.error('Unable to load core application "%s". System will be instable', module_name)
                    self.crash_report.report_exception({
                        'message': 'Unable to load core application "%s". System will be instable', module_name,
                        'module_name': module_name
                    })

            finally:
                # clear module loading tree (replace it with clear() available in python3)
                del self.__module_loading_tree[:]

        # load installed modules
        for module_name in self.configured_modules:
            try:
                # load module
                self.__load_module(module_name, local_modules)

                # register renderers
                if module_name in self.__modules_instances and isinstance(self.__modules_instances[module_name], CleepRenderer):
                    config = self.__modules_instances[module_name]._get_renderer_config()
                    self.formatters_broker.register_renderer(module_name, config['profiles'])

                # store rpc wrappers
                if module_name in self.__modules_instances and isinstance(self.__modules_instances[module_name], CleepRpcWrapper):
                    self.logger.debug('Store RpcWrapper instance "%s"', module_name)
                    self.__rpc_wrappers.append(module_name)

            except Exception as e:
                # flag modules has in error
                self.__modules_in_error[module_name] = str(e)
                self.logger.exception('Unable to load application "%s" or one of its dependencies:', module_name)
                # TODO report error if not locally installed module

            finally:
                # clear module loading tree (replace it with clear() available in python3)
                del self.__module_loading_tree[:]

        # compute compat string
        modules_versions = {module_name: module['version'] for module_name, module in self.modules.items()}
        modules_versions['cleep'] = CLEEP_VERSION
        for module_name, module in self.modules.items():
            module.update({
                'compat': module.get('compat', ''),
                'compatible': Tools.compare_compat_string(module.get('compat', ''), modules_versions),
            })

        # execution step: INIT->CONFIG
        self.bootstrap['execution_step'].step = ExecutionStep.CONFIG

        # finalize loading process
        for module_name in self.modules:
            # fix final library status
            if module_name in self.__modules_loaded_as_dependency:
                self.modules[module_name]['library'] = self.__modules_loaded_as_dependency[module_name]

        # start installed modules
        for module_name, module_ in self.__modules_instances.items():
            module_.start()

        # wait for all modules to be completely loaded
        self.logger.info('Waiting for end of modules configuration...')
        for module_join_event in self.__module_join_events:
            module_join_event.wait()
        self.logger.info('All applications are configured.')
        self.bootstrap['core_join_event'].set()

        # check if modules are properly configured and started
        # OBSOLETE seems to be obsolete code !
        #for module_name, module_ in self.__modules_instances.items():
        #    if not module_.is_alive():
        #        self.__modules_in_error[module_name] = 'Application "%s" configuration failed' % module_name
        #        # TODO report error if not locally installed module

        # execution step: CONFIG->RUN
        self.bootstrap['execution_step'].step = ExecutionStep.RUN

        self.__modules_loaded = True
        self.logger.debug('All modules are loaded')

    def wait_for_apps_started(self):
        """
        Wait for all applications are started

        Note:
            This method is blocking !

        Returns:
            bool: True if everything is started, False if an app is blocked or if one of app startup failed
        """
        if not self.bootstrap['core_join_event'].wait(self.MODULES_SYNC_TIMEOUT):
            self.logger.fatal('Startup takes too much time. An app may be blocked. Cleep may not run properly')
            return False

        if len(self.__modules_in_error.keys()) > 0:
            self.logger.error('Following apps are in error: %s', self.__modules_in_error)
            return False

        return True

    def unload_modules(self):
        """
        Unload all modules stopping them
        """
        # stop all running modules and unimport them
        for module_name in self.__modules_instances:
            self.__modules_instances[module_name].stop()

        # clear collection
        self.__modules_instances.clear()

    def get_module_device(self, uuid):
        """
        Return module that owns specified device

        Args:
            uuid (string): device identifier

        Returns:
            string: module name or None if device was not found
        """
        devices = self.get_devices()
        for module_name in devices:
            if uuid in devices[module_name]:
                return module_name

        return None

    def get_module_devices(self, module_name):
        """
        Return module devices
        
        Args:
            module_name (string): module name
        
        Returns:
            list: list of devices::

                [
                    {'uuid':'', 'name':''},
                    ...
                ]

        Raises:
            CommandError: if application doesn't exist
        """
        if module_name not in self.modules:
            raise InvalidParameter('Application "%s" doesn\'t exist' % module_name)

        # search module devices
        devices = self.get_devices()
        return devices[module_name] if module_name in devices else []

    def get_devices(self):
        """
        Return dict of modules devices

        Returns:
            dict: dict of devices by module::

                {
                    module1: 
                        device uuid: {
                            device properties,
                            ...
                        },
                        ...
                    },
                    module2: ...
                }

        """
        devices = {}
        for module_name in self.__modules_instances:
            try:
                if isinstance(self.__modules_instances[module_name], CleepModule):
                    devices[module_name] = self.__modules_instances[module_name].get_module_devices()
            except Exception:
                self.logger.exception('Unable to get devices of application "%s"', module_name)

        return devices

    def get_module_infos(self, module_name):
        """
        Returns infos of specified module

        Args:
            module_name (string): module name

        Returns:
            dict: module infos or empty dict if module not found::
                
                {
                    name: str
                    version: str
                    ...
                }

        """
        if module_name not in self.modules:
            return {}

        events = self.events_broker.get_modules_events()
        module = copy.deepcopy(self.modules[module_name])

        # add module config
        try:
            module['config'] = self.__modules_instances[module_name].get_module_config() if module_name in self.__modules_instances else {}
        except:
            self.logger.exception('Unable to retrieve "%s" app config. Return empty config', module_name)
            module['config'] = {};
            
        # add module events
        module['events'] = events[module_name] if module_name in events else []
    
        # started flag
        module['started'] = self.__is_module_started(module_name)

        # add library is loaded by
        module['loadedby'] = self.__dependencies[module_name] if module_name in self.__dependencies else []

        return module

    def get_modules_configs(self):
        """
        Return modules configs only

        Returns:
            dict: modules configurations::

            {
                module name (string): module configuration (dict)
                ...
            }

        """
        configs = {}

        installed_apps = self._get_modules(lambda name,module,modules: name in modules and modules[name]['installed'])
        for app_name, app in installed_apps.items():
            try:
                configs[app_name] = self.__modules_instances[app_name].get_module_config() if app_name in self.__modules_instances else {}
            except:
                self.logger.exception('Unable to get app "%s" config', app_name)

        return configs

    def __is_module_started(self, module_name):
        """
        Check if module is started and running

        Returns:
            bool: True if module is ok
        """
        # check if error occured during loading
        started = not module_name in self.__modules_in_error.keys()
        if not started:
            return False

        # also check if thread is running
        return self.__modules_instances[module_name].is_alive() if started and module_name in self.__modules_instances else False


    def get_installable_modules(self):
        """
        Returns dict of installable modules. It also returns modules installed as library.

        Returns:
            dict: dict of modules::

                {
                    module name: {
                        name: '',
                        version: '',
                        ...
                    },
                    ...
                }

        """
        return self._get_modules(lambda name,module,modules: name in modules and (modules[name]['library'] or not modules[name]['installed']))

    def get_modules(self):
        """
        Returns dict of installed modules. It also returned modules installed as library.

        Returns:
            dict: dict of modules::

                {
                    module name: {
                        name: '',
                        version: '',
                        ...
                    },
                    ...
                }

        """
        installed_modules = self._get_modules(lambda name,module,modules: name in modules and modules[name]['installed'])
        modules = {}

        for module_name, module in installed_modules.items():
            try:
                # drop not launched modules
                #if module_name not in self.__modules_instances:
                #    self.logger.trace('Drop not started module "%s"', module_name)
                #    continue
                modules[module_name] = self.get_module_infos(module_name)

            except: # pragma: no cover
                self.logger.exception('Unable to get data from application "%s"', module_name)

        return modules

    def _get_modules(self, module_filter=None):
        """
        Returns modules adding possibility to filter them

        Args:
            module_filter (function): filtering function. Params: module name, module data, all modules
        
        Returns:
            dict: dict of modules::

                {
                    module name: {
                        name: '',
                        version: '',
                        ...
                    },
                    ...
                }

        """
        # check params
        if module_filter is not None and not callable(module_filter):
            raise InvalidParameter('Parameter "module_filter" must be callable')

        # fix module_filter
        if module_filter is None:
            module_filter = lambda mod_name, mod_data, all_mods: True
        
        all_modules = copy.deepcopy(self.modules)
        filtered_modules = {}
        for module_name, module in {k:v for k,v in all_modules.items() if module_filter(k,v,all_modules)}.items():
            filtered_modules[module_name] = module

        return filtered_modules
            
    def get_module_commands(self, module):
        """
        Returns list of module commands

        Args:
            module (string): module name

        Returns:
            list: list of commands or empty list if module not found::

                ['command1', 'command2', ...]

        """
        if module is not None:
            return self.__modules_instances[module].get_module_commands() if module in self.__modules_instances else []

        return {module_name:module_instance.get_module_commands() for (module_name, module_instance) in self.__modules_instances.items()}

    def get_module_documentation(self, module_name, no_cache=False):
        """
        Return module documentation

        Args:
            module_name (str): module name
            no_cache (bool): True to not use cached documentation

        Returns:
            dict: module documentation::

                {
                    command (dict): command documentation
                    ...
                }

        """
        if module_name not in self.__modules_instances:
            raise InvalidParameter('Application "%s" is not installed' % module_name)

        return self.__modules_instances[module_name].get_documentation(no_cache)

    def check_module_documentation(self, module_name, with_details=False):
        """
        Return module documentation validity

        Args:
            module_name (str): module name
            with_details (bool): add check details to output

        Returns:
            dict: module documentation validity::

                {
                    command (dict): command documentation validity
                    ...
                }

        """
        if module_name not in self.__modules_instances:
            raise InvalidParameter('Application "%s" is not installed' % module_name)

        return self.__modules_instances[module_name].check_documentation(with_details)

    def is_module_loaded(self, module):
        """
        Simply returns True if specified module is loaded
        
        Args:
            module (string): module name

        Returns:
            bool: True if module loaded, False otherwise
        """
        return module in self.__modules_instances

    def get_modules_debug(self):
        """
        Return dict of installed modules or libraries debug flag

        Returns:
            dict: dict of modules/libraries debug flag::
            
                {
                    modulename (bool): debug flag
                    ...
                }

        """
        debugs = {}
        for module in self.modules:
            # only get debug value of installed modules
            if not self.modules[module]['installed']:
                continue

            # get debug status
            try:
                debugs[module] = {
                    'debug': self.__modules_instances[module].is_debug_enabled()
                }

            except:
                self.logger.exception('Unable to get application %s debug status:', module)
                debugs[module] = {
                    'debug': False
                }

        # append core modules
        debugs.update({
            'inventory': {
                'debug': self.is_debug_enabled()
            },
            'rpc': {
                'debug': self.__rpcserver.is_debug_enabled()
            }
        })

        return debugs

    def set_rpc_debug(self, debug):
        """
        Set debug on rpcserver

        Args:
            debug (bool): debug enabled or not
        """
        self.__rpcserver.set_debug(debug)

    def set_rpc_cache_control(self, cache_enabled):
        """
        Set RPC server cache control

        Args:
            cache_enabled (bool): True to enable cache
        """
        self.__rpcserver.set_cache_control(cache_enabled)

    def get_renderers(self):
        """
        Return renderers from events broker

        Returns:
            list: list of renderers with their handled profiles
        """
        return self.formatters_broker.get_renderers_profiles()

    def get_modules_events(self):
        """
        Return modules events

        Returns:
            dict: dict of modules events::

                {
                    module1: [event1, event2, ...],
                    module2: [event1],
                    ...
                }

        """
        return self.events_broker.get_modules_events()

    def get_used_events(self):
        """
        Return used events

        Returns:
            list: list of used events
        """
        return self.events_broker.get_used_events()

    def rpc_wrapper(self, route, request):
        """
        Rpc wrapper is called by rpc server when default / POST route is called.
        Inventory get all loaded CleepRpcWrapperModule modules and push the bottle request object.
        See bottle documentation for request object description https://bottlepy.org/docs/dev/tutorial.html#request-data
        """
        for module_name in self.__rpc_wrappers:
            try:
                self.__modules_instances[module_name]._wrap_request(route, request)
            except:
                self.logger.exception('RpcWrapper wrap_request function failed:')

    def get_drivers(self):
        """
        Return drivers
        """
        return self.bootstrap['drivers'].get_all_drivers()

    def __get_object_size(self, obj): # pragma: no cover
        """
        Return memory size of specified object instance. Useful to monitor module instance size

        Args:
            obj (object): object instance

        Returns:
            int: memory size of instance

        Notes:
            Code from https://stackoverflow.com/a/30316760
        """
        BLACKLIST = type, ModuleType, FunctionType

        if isinstance(obj, BLACKLIST):
            return 0

        seen_ids = set()
        size = 0
        objects = [obj]
        while objects:
            need_referents = []
            for obj in objects:
                if not isinstance(obj, BLACKLIST) and id(obj) not in seen_ids:
                    seen_ids.add(id(obj))
                    size += sys.getsizeof(obj)
                    need_referents.append(obj)
            objects = get_referents(*need_referents)

        return size

    def __memory_monitoring(self): # pragma: no cover
        """
        Memory monitoring task
        """
        self.logger.info('========== MEMORY STATUS ==========')
        for module_name, module_instance in self.__modules_instances.items():
            self.logger.info(' - %s: %d', (module_name, self.__get_object_size(module_instance)))

    def get_apps_health(self):
        """
        Return list of not started applications

        Returns:
            list: list of not started application names
        """
        health = {}
        installed_modules = self._get_modules(lambda name,module,modules: name in modules and modules[name]['installed'])
        for module_name in installed_modules:
            health[module_name] = self.__is_module_started(module_name)

        return health

    def register_remote_access_url(self, url, command_sender):
        """
        Register url for device remote access. Only one url per application allowed.

        Args:
            url (str): url of remote access
            command_sender (str): name of caller
        """
        self.__remote_access_urls[command_sender] = url

    def unregister_remote_access_url(self, command_sender):
        """
        Unregister remote access url

        Args:
            command_sender (str): name of caller
        """
        if command_sender in self.__remote_access_urls:
            del self.__remote_access_urls[command_sender]

    def get_remote_access_urls(self):
        """
        Return all remote access urls

        Returns:
            dict: dist of registered remote access urls::

                {
                    app name: remote access url (str),
                    ...
                }
        """
        return self.__remote_access_urls
