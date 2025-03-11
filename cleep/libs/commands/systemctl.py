#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.console import Console
from datetime import datetime, timezone
from dateutil.parser import parse as du_parse
import logging
import json

class Systemctl(Console):
    """
    Systemctl command helper
    """

    CMD_SYSTEMCTL = "/usr/bin/systemctl"
    CMD_JOURNALCTL = "/usr/bin/journalctl"

    PRIORITIES = [
        "emergency",
        "alert",
        "critical",
        "error",
        "warn",
        "notice",
        "info",
        "debug"
    ]

    def __init__(self):
        """
        Constructor
        """
        Console.__init__(self)

        self.logger = logging.getLogger(self.__class__.__name__)

    def get_service_status(self, service_name):
        """
        Get service status using systemctl command

        Args:
            service_name (str): service name

        Returns:
            dict: service infos or None if command failed::

                {
                    state (str): current service state (active/inactive/failed/activating/deactivating/maintenance/reloading/refreshing)
                    substate (str): current service substate (dead...)
                    pid (int): current service PID. 0 if service is not running
                    path (str): service script path
                    start (date): service start date or None if not started
                    stop (date): service stop date or None if running
                    restarts (int): number of service restarts
                    runtime (int): number of seconds since process was started
                    command (str): executed service command
                }

        """
        returncode, stdout = self.__run_systemctl_command("show", service_name)
        if returncode != 0:
            return None

        keys = self.__parse_show_stdout(stdout)
        state = keys.get("ActiveState", "")
        now_tz = datetime.utcnow().replace(tzinfo=timezone.utc)
        start = self.__parse_datetime(keys.get("ActiveEnterTimestamp", ""), now_tz)
        runtime = (now_tz-start).seconds
        exec_start = self.__parse_execstart_field(keys.get("ExecStart", ""))
        command = exec_start.get("argv[]", None)

        return {
            "state": state,
            "substate": keys.get("SubState", ""),
            "pid": self.__parse_integer(keys.get("MainPID", "0")),
            "path": keys.get("FragmentPath", ""),
            "start": start,
            "stop": None if state == "active" else self.__parse_datetime(keys.get("ActiveExitTimestamp", "")),
            "restarts": self.__parse_integer(keys.get("NRestarts", "0")),
            "runtime": runtime,
            "command": command,
        }

    def start_service(self, service_name):
        """
        Start specified service name

        Args:
            service_name (str): service name

        Returns:
            bool: True if command succeed, False otherwise
        """
        returncode, _ = self.__run_systemctl_command("start", service_name)
        return returncode == 0

    def stop_service(self, service_name):
        """
        Stop specified service name

        Args:
            service_name (str): service name

        Returns:
            bool: True if command succeed, False otherwise
        """
        returncode, _ = self.__run_systemctl_command("stop", service_name)
        return returncode == 0

    def restart_service(self, service_name):
        """
        Restart specified service name

        Args:
            service_name (str): service name

        Returns:
            bool: True if command succeed, False otherwise
        """
        returncode, _ = self.__run_systemctl_command("restart", service_name)
        return returncode == 0

    def get_service_logs(self, service_name, minutes=5, lines=None, errors=False):
        """
        Get service logs

        Args:
            service_name (str): service name
            minutes (int): return logs since specified minutes number. Defaults to 5
            lines (int): number of messages to retrieve
            errors (bool): return only error messages. Defaultis to False

        Returns:
            list: list of log messages or None if command failed::

                [(datetime (datetime), priority (str), message (str)),...]

        """
        priority = 3 if errors else None
        returncode, stdout = self.__run_journalctl_command(service_name, minutes, lines, priority)

        if returncode != 0:
            return None

        output = []
        try:
            lines = json.loads("["+','.join(stdout)+"]")
            for line in lines:
                timestamp = self.__parse_integer(line.get("__REALTIME_TIMESTAMP", "0"))
                dt = datetime.fromtimestamp(timestamp // 1000000)
                priority = self.__parse_integer(line.get("PRIORITY"))
                output.append((dt, Systemctl.PRIORITIES[priority], line.get("MESSAGE")))
            return output
        except Exception as error:
            self.logger.exception("Unable to parse %s service logs:", service_name)
            return None

    def __run_systemctl_command(self, command, service_name):
        """
        Run systemctl command

        Args:
            command (str): command name (start, stop...)
            service_name (str): service name

        Returns:
            tuple: command status code and full response::

                ( returncode (int), stdout (list) )

        """
        cmd = [Systemctl.CMD_SYSTEMCTL, command, service_name]
        self.logger.trace('Cmd: %s' % cmd)
        resp = self.command(cmd)
        self.logger.trace('Cmd "%s" resp: %s' % (cmd, resp))

        return (resp.get("returncode"), resp.get("stdout", []))

    def __run_journalctl_command(self, service_name, minutes=5, lines=None, priority=None):
        """
        Run journalctl command. Output is formatted as json

        Args:
            service_name (str): service name
            minutes (int): logs within last minutes to return. Defaults to 5
            lines (int): number of messages to retrieve
            priority (int): priority level message to retrieve. 0 for emergency, 1 for alert,
                            2 for critical, 3 for error, 4 for warn, 5 for notice, 6 for info,
                            7 for debug, see Systemctl.PRIORITIES. Defaults to None

        Returns:
            tuple: command status code and full response::

                ( returncode (int), stdout (list) )

        """
        cmd = [Systemctl.CMD_JOURNALCTL, "-u", service_name, "--no-pager", "--since", f"{minutes} minutes ago", "-r", "--quiet", "-o", "json"]
        if lines:
            cmd.extend(["-n", str(lines)])
        if priority:
            cmd.extend(["-p", str(priority)])

        self.logger.trace('Cmd: %s' % cmd)
        resp = self.command(cmd)
        self.logger.trace('Cmd "%s" resp: %s' % (cmd, resp))

        return (resp.get("returncode"), resp.get("stdout", []))

    def __parse_datetime(self, string, default=None):
        """
        Parse specified string to python datetime

        Args:
            string (str): string datetime from systemctl command
            default (any): default value returned if error occured

        Returns:
            datetime: parsed datetime or default if unable to parse string
        """
        try:
            return du_parse(string)
        except:
            self.logger.trace('Unable to parse string "%s" as datetime', string)
            return default

    def __parse_integer(self, string):
        """
        Parse specified string to python integer

        Args:
            string (str): string number to parse

        Returns:
            int: parsed string or 0 if unable to parse string
        """
        try:
            return int(string)
        except:
            self.logger.trace('Unable to parse string "%s" as integer', string)
            return 0

    def __parse_show_stdout(self, stdout):
        """
        Parse "systemctl show" stdout

        Args:
            stdout (list): list of stdout lines

        Returns:
            dict: key-value of parsed stdout::

            {
                key: value,
                ...
            }

        """
        output = {}
        for line in stdout:
            try:
                [key, value] = line.split("=", 1)
                output[key] = value
            except Exception as error:
                # do not failed on split error
                self.logger.trace("Error parsing systemctl show stdout: %s [%s]", line, str(error))
        return output

    def __parse_execstart_field(self, execstart):
        """
        Parse ExecStart field received from systemctl show command

        Args:
            execstart (str): ExecStart field string

        Returns:
            dict: parsed fields as dict, empty dict if something failed::

                {
                    key (str): value (str)
                    ...
                }

        """
        try:
            splits = execstart.split(" ; ")
            splits[0] = splits[0].replace("{ ", "")
            splits[-1] = splits[0].replace(" }", "")
            parsed = {}
            for split in splits:
                key, value = split.split("=", 1)
                parsed[key] = value
            return parsed
        except Exception as error:
            self.logger.trace("Error: %s", str(error))
            return {}
