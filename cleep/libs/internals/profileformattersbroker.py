#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import importlib
from cleep.exception import MissingParameter, InvalidParameter
from cleep.common import CORE_MODULES
from cleep.libs.internals.tools import full_split_path

__all__ = ["ProfileFormattersBroker"]


class ProfileFormattersBroker:
    """
    ProfileFormatters broker is in charge of centralizing all formatters
    It also ensures formatters use exiting events
    """

    # final dot mandatory to allow unit tests
    PYTHON_CLEEP_MODULES_IMPORT_PATH = "cleep.modules."
    MODULES_DIR = "../../modules"

    def __init__(self, debug_enabled):
        """
        Constructor

        Args:
            debug_enabled (bool): debug flag
        """
        # members
        self.logger = logging.getLogger(self.__class__.__name__)
        if debug_enabled:
            self.logger.setLevel(logging.DEBUG)
        self.events_broker = None
        # list of renderer module names with format::
        #
        #   [
        #       'renderer_module_name1',
        #       'renderer_module_name2',
        #       ...
        #   ]
        #
        self.__renderers = []
        # dict of formatters sorted by event->profile->module::
        #
        #   {
        #       'event#1': {
        #           'profile#1': {
        #               'module#1': formatter_instance#1,
        #               ...
        #           },
        #           'profile#2': {
        #               'module#1': formatter_instance#1
        #               'module#3': formatter_instance#3
        #           }
        #       },
        #       'event#2': {
        #           'profile#1': ...,
        #           'profile#3': ...
        #       },
        #       ...
        #   }
        #
        # Existing formatters contains list of all found formatters in current installation...
        self.__existing_formatters = {}
        # List of formatters by events
        #
        #   {
        #       event1: {
        #           module1: formatter1
        #           ...
        #       },
        #       event2: {
        #           module1: formatter2,
        #           module2: formatter3
        #       },
        #       ...
        #   }
        #
        self.__formatters = {}
        # Mapping list of referenced renderer module profiles with format::
        #
        #   {
        #       'module_name1': [
        #           'profile_name1',
        #           'profile_name2',
        #       ],
        #       'module_name2': [
        #           'profile_name3',
        #           ...
        #       ],
        #       ...
        #   }
        #
        self.__renderers_profiles = {}
        self.crash_report = None

    def configure(self, bootstrap):
        """
        Configure broker

        Args:
            bootstrap (dict): bootstrap objects
        """
        # set members
        self.events_broker = bootstrap["events_broker"]

        # configure crash report
        self.crash_report = bootstrap["crash_report"]

        # load formatters
        self.__load_formatters()

    def __get_formatter_class_name(self, filename, module):
        """
        Search for formatter class name trying to match filename with item in module

        Args:
            filename (string): filename (without extension)
            module (module): python module
        """
        return next(
            (item for item in dir(module) if item.lower() == filename.lower()), None
        )

    def __load_formatters(self):
        """
        Load all formatters available in current Cleep installation

        Raises:
            Exception if internal error occured
        """
        self.logger.debug("Loading modules formatters")
        modules_path = os.path.join(os.path.dirname(__file__), self.MODULES_DIR)
        if not os.path.exists(modules_path):
            self.crash_report.report_exception(
                {"message": "Invalid module path", "path": modules_path}
            )
            raise Exception("Invalid modules path")
        self.__load_formatters_from_path(modules_path, False)

        self.__dump_existing_formatters()

    def __load_formatters_from_path(self, path, is_core):
        """
        Load formatters from specified path

        Args:
            path (str): path to walk through
        """
        self.logger.trace(" Searching formatters from %s", os.path.normpath(path))
        for root, _, filenames in sorted(os.walk(path)):
            for filename in filenames:
                try:
                    fullpath = os.path.join(root, filename)
                    (formatter, ext) = os.path.splitext(filename)
                    parts = full_split_path(fullpath)
                    module_name = parts[-2]
                    if ext == ".py" and formatter.lower().endswith("formatter"):
                        self.__load_formatter(module_name, formatter)

                except AttributeError:  # pragma: no cover
                    self.logger.exception(
                        'Formatter "%s" was not loaded: it has surely invalid name. Please refer to coding rules.',
                        formatter,
                    )

                except Exception:
                    self.logger.exception(
                        'Formatter "%s" was not loaded: it has some problem from inside. Please check code.',
                        formatter,
                    )


    def __load_formatter(self, module_name, formatter):
        """
        Load specified file as formatter

        Args:
            module_name (str): module name that holds the formatter
            formatter (str): formatter name
        """
        self.logger.debug(' Found "%s.%s"', module_name, formatter)
        import_path = f"{self.PYTHON_CLEEP_MODULES_IMPORT_PATH}{module_name}.{formatter}"
        self.logger.trace(" Import path %s", import_path)
        mod_ = importlib.import_module(import_path)
        formatter_class_name = self.__get_formatter_class_name(formatter, mod_)
        if formatter_class_name:
            formatter_class_ = getattr(mod_, formatter_class_name)
            formatter_instance_ = formatter_class_(
                {"events_broker": self.events_broker}
            )

            # save reference on module where formatter was found
            if formatter_instance_.event_name not in self.__existing_formatters:
                self.__existing_formatters[formatter_instance_.event_name] = {}
            if (
                formatter_instance_.profile_name
                not in self.__existing_formatters[formatter_instance_.event_name]
            ):
                self.__existing_formatters[formatter_instance_.event_name][
                    formatter_instance_.profile_name
                ] = {}
            self.__existing_formatters[formatter_instance_.event_name][
                formatter_instance_.profile_name
            ][module_name] = formatter_instance_
            self.logger.debug(
                ' Set formatter "%s" from module "%s" for event "%s" and profile "%s"',
                formatter_class_name,
                module_name,
                formatter_instance_.event_name,
                formatter_instance_.profile_name,
            )
        else:
            self.logger.error(
                'Formatter class name must have the same name than filename in "%s"',
                formatter,
            )

    def __dump_existing_formatters(self):  # pragma: no cover
        """
        Dump existing formatters. Debug purpose only
        """
        if self.logger.getEffectiveLevel() <= logging.DEBUG:
            self.logger.trace("Existing formatters :")
            for event in self.__existing_formatters:
                self.logger.trace("\t%s {", event)
                for profile in self.__existing_formatters[event]:
                    self.logger.trace("\t\t%s {", profile)
                    for renderer in self.__existing_formatters[event][profile]:
                        self.logger.trace(
                            "\t\t\t%s: %s",
                            renderer,
                            self.__existing_formatters[event][profile][
                                renderer
                            ].__class__.__name__,
                        )
                    self.logger.trace("\t\t}")
                self.logger.trace("\t}")

    def register_renderer(self, module_name, module_profiles):
        """
        Register new renderer

        Args:
            module_name (string): name of renderer (module name)
            module_profiles (list<RendererProfile>): list of profiles supported by module

        Raises:
            MissingParameter, InvalidParameter
        """
        # check values
        if module_profiles is None:
            raise MissingParameter('Parameter "module_profiles" is missing')
        if not isinstance(module_profiles, list):
            raise InvalidParameter('Parameter "module_profiles" must be a list')
        if len(module_profiles) == 0:
            raise InvalidParameter(
                'Parameter "module_profiles" must contains at least one profile'
            )
        self.logger.debug(
            'Register new renderer "%s" with profiles: %s',
            module_name,
            [profile.__name__ for profile in module_profiles],
        )

        # update renderers list
        self.__renderers.append(module_name)

        # update renderers profiles names list (not instance!)
        self.__renderers_profiles[module_name] = [
            profile.__name__ for profile in module_profiles
        ]

        # update renderer profiles list
        for profile in module_profiles:
            for event_name, handled_profiles in self.__existing_formatters.items():
                if (
                    profile.__name__ not in handled_profiles
                    or len(handled_profiles) == 0
                ):
                    # not useful formatter for this profile
                    continue

                # search best formatter
                best_formatter = self.__get_best_formatter(
                    module_name, handled_profiles[profile.__name__]
                )
                self.logger.trace(
                    'Best formatter for event "%s" for app "%s": %s',
                    event_name,
                    module_name,
                    best_formatter,
                )
                if not best_formatter:
                    self.logger.warning(
                        'No formatter found for event "%s" requested by "%s" app "%s" profile',
                        event_name,
                        module_name,
                        profile.__name__,
                    )
                    continue

                # save formatter
                if event_name not in self.__formatters:
                    self.__formatters[event_name] = {}
                self.__formatters[event_name][module_name] = best_formatter

        self.logger.debug("List of formatters: %s", self.__formatters)

    def __get_best_formatter(self, module_name, formatters):
        """
        Return best formatters focusing app provided formatter first, then core one and finally third part

        Args:
            module_name (string): module name to search best formatter for
            formatters (dict): list of formatters for event and profile
        """
        best = {
            "formatter": None,
            "fromcore": False,
            "fromapp": False,
        }
        self.logger.debug("Best in formatters: %s", formatters)
        for app_name, formatter in formatters.items():
            if best["formatter"] is None:
                # first loop
                best.update(
                    {
                        "formatter": formatter,
                        "fromcore": app_name in CORE_MODULES,
                        "fromapp": app_name == module_name,
                    }
                )
            elif app_name == module_name:
                # force using formatter provided by application
                self.logger.trace(
                    'Found better formatter from app "%s" itself', module_name
                )
                best.update(
                    {
                        "formatter": formatter,
                        "fromcore": app_name in CORE_MODULES,
                        "fromapp": app_name == module_name,
                    }
                )
            elif (
                not best["fromapp"]
                and not best["fromcore"]
                and app_name in CORE_MODULES
            ):
                # force using formatter provided by core modules
                self.logger.trace('Found better formatter from core app "%s"', app_name)
                best.update(
                    {
                        "formatter": formatter,
                        "fromcore": app_name in CORE_MODULES,
                        "fromapp": app_name == module_name,
                    }
                )

        return best["formatter"]

    def get_renderers_profiles(self):
        """
        Return list of profiles handled by renderers

        Returns:
            dict: dict of profile handled by renderers::

                {
                    module_name (string): [
                        profile_name (string),
                        ...
                    ],
                    ...
                }

        """
        return self.__renderers_profiles

    def get_renderers(self):
        """
        Returns list of renderers (aka module)

        Returns:
            list: list of renderers::

                [
                    module_name (string),
                    ...
                ]

        """
        return self.__renderers

    def get_renderers_formatters(self, event_name):
        """
        Return all event formatters by modules that are loaded

        Args:
            event_name (string): event name to search formatters for

        Returns:
            dict: Formatter instances for specified event for each modules that implements it or empty dict if no formatter for this event::

                {
                    module name (string): formatter instance (ProfileFormatter)
                    ...
                }

        """
        return self.__formatters.get(event_name, {})
