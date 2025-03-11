#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace("tests/", ""))
from systemctl import Systemctl
from cleep.libs.tests.lib import TestLib
import unittest
import logging
from cleep.libs.tests.common import get_log_level
from unittest.mock import Mock, patch
import datetime
from dateutil.tz import tzlocal
from copy import deepcopy
from cleep.libs.tests.common import AnyArg

LOG_LEVEL = get_log_level()

JOURNALCTL_OUTPUT = [
    '{"_TRANSPORT":"syslog","_SYSTEMD_INVOCATION_ID":"b7dce7dfc8d045ffbeeff586c0c9948d","SYSLOG_RAW":"<4>Mar 11 16:06:51 ngrok[30994]: t=2025-03-11T16:06:51+0100 lvl=warn msg=\\"tunnel not found\\" pg=/api/tunnels/cleep id=df87d3495ef29edf name=cleep\\n","_COMM":"ngrok","SYSLOG_TIMESTAMP":"Mar 11 16:06:51 ","SYSLOG_IDENTIFIER":"ngrok","_SYSTEMD_CGROUP":"/system.slice/ngrok.service","MESSAGE":"t=2025-03-11T16:06:51+0100 lvl=warn msg=\\"tunnel not found\\" pg=/api/tunnels/cleep id=df87d3495ef29edf name=cleep","_SYSTEMD_SLICE":"system.slice","_UID":"0","__MONOTONIC_TIMESTAMP":"9096421177768","__CURSOR":"s=dbd94044e5b74ede8cf84729bbadd466;i=1542ee;b=488458ece6654edebf681e0a39e4836d;m=845ecf3f9a8;t=63012704a32b8;x=852cf1578ea81999","_EXE":"/var/opt/cleep/modules/bin/ngrok/ngrok","_SYSTEMD_UNIT":"ngrok.service","__REALTIME_TIMESTAMP":"1741705611719352","_PID":"30994","PRIORITY":"4","_SOURCE_REALTIME_TIMESTAMP":"1741705611717672","SYSLOG_PID":"30994","_BOOT_ID":"488458ece6654edebf681e0a39e4836d","_CAP_EFFECTIVE":"1ffffffffff","_GID":"0","_CMDLINE":"/var/opt/cleep/modules/bin/ngrok/ngrok service run --config /var/opt/cleep/modules/bin/ngrok/ngrok.yml","_MACHINE_ID":"b563bb22f7e54d49995e5fdfa85aa167","_HOSTNAME":"cleepdev4"}',
    '{"_SYSTEMD_CGROUP":"/system.slice/ngrok.service","_HOSTNAME":"cleepdev4","SYSLOG_IDENTIFIER":"ngrok","SYSLOG_FACILITY":"3","__REALTIME_TIMESTAMP":"1741705611718750","_CMDLINE":"/var/opt/cleep/modules/bin/ngrok/ngrok service run --config /var/opt/cleep/modules/bin/ngrok/ngrok.yml","_SYSTEMD_SLICE":"system.slice","_EXE":"/var/opt/cleep/modules/bin/ngrok/ngrok","_GID":"0","__CURSOR":"s=dbd94044e5b74ede8cf84729bbadd466;i=1542ed;b=488458ece6654edebf681e0a39e4836d;m=845ecf3f74e;t=63012704a305e;x=1dc7244347fb088a","_TRANSPORT":"stdout","_SYSTEMD_INVOCATION_ID":"b7dce7dfc8d045ffbeeff586c0c9948d","_STREAM_ID":"092c2b1a35ff416483c77c7c7fcf1b12","_BOOT_ID":"488458ece6654edebf681e0a39e4836d","_SYSTEMD_UNIT":"ngrok.service","PRIORITY":"6","_UID":"0","__MONOTONIC_TIMESTAMP":"9096421177166","MESSAGE":"t=2025-03-11T16:06:51+0100 lvl=info msg=end pg=/api/tunnels/cleep id=df87d3495ef29edf status=404 dur=896.662µs","_PID":"30994","_CAP_EFFECTIVE":"1ffffffffff","_COMM":"ngrok","_MACHINE_ID":"b563bb22f7e54d49995e5fdfa85aa167"}',
    '{"_EXE":"/var/opt/cleep/modules/bin/ngrok/ngrok","_MACHINE_ID":"b563bb22f7e54d49995e5fdfa85aa167","_SYSTEMD_SLICE":"system.slice","MESSAGE":"t=2025-03-11T16:06:51+0100 lvl=warn msg=\\"tunnel not found\\" pg=/api/tunnels/cleep id=df87d3495ef29edf name=cleep","_SYSTEMD_INVOCATION_ID":"b7dce7dfc8d045ffbeeff586c0c9948d","_SYSTEMD_UNIT":"ngrok.service","__REALTIME_TIMESTAMP":"1741705611718750","_CAP_EFFECTIVE":"1ffffffffff","PRIORITY":"6","_BOOT_ID":"488458ece6654edebf681e0a39e4836d","_UID":"0","SYSLOG_FACILITY":"3","__MONOTONIC_TIMESTAMP":"9096421177166","_COMM":"ngrok","_PID":"30994","_HOSTNAME":"cleepdev4","SYSLOG_IDENTIFIER":"ngrok","_GID":"0","_STREAM_ID":"092c2b1a35ff416483c77c7c7fcf1b12","_CMDLINE":"/var/opt/cleep/modules/bin/ngrok/ngrok service run --config /var/opt/cleep/modules/bin/ngrok/ngrok.yml","_SYSTEMD_CGROUP":"/system.slice/ngrok.service","__CURSOR":"s=dbd94044e5b74ede8cf84729bbadd466;i=1542ec;b=488458ece6654edebf681e0a39e4836d;m=845ecf3f74e;t=63012704a305e;x=53ddea857e2ae115","_TRANSPORT":"stdout"}',
    '{"__CURSOR":"s=dbd94044e5b74ede8cf84729bbadd466;i=1542eb;b=488458ece6654edebf681e0a39e4836d;m=845ecf3f10e;t=63012704a2a1d;x=755849a9e7bd1a4","SYSLOG_IDENTIFIER":"ngrok","_CAP_EFFECTIVE":"1ffffffffff","_UID":"0","__MONOTONIC_TIMESTAMP":"9096421175566","_TRANSPORT":"stdout","_BOOT_ID":"488458ece6654edebf681e0a39e4836d","_COMM":"ngrok","_SYSTEMD_INVOCATION_ID":"b7dce7dfc8d045ffbeeff586c0c9948d","_HOSTNAME":"cleepdev4","PRIORITY":"6","_MACHINE_ID":"b563bb22f7e54d49995e5fdfa85aa167","MESSAGE":"t=2025-03-11T16:06:51+0100 lvl=info msg=start pg=/api/tunnels/cleep id=df87d3495ef29edf","_GID":"0","_SYSTEMD_UNIT":"ngrok.service","_SYSTEMD_SLICE":"system.slice","_PID":"30994","_STREAM_ID":"092c2b1a35ff416483c77c7c7fcf1b12","_SYSTEMD_CGROUP":"/system.slice/ngrok.service","_EXE":"/var/opt/cleep/modules/bin/ngrok/ngrok","SYSLOG_FACILITY":"3","_CMDLINE":"/var/opt/cleep/modules/bin/ngrok/ngrok service run --config /var/opt/cleep/modules/bin/ngrok/ngrok.yml","__REALTIME_TIMESTAMP":"1741705611717149"}',
    '{"SYSLOG_IDENTIFIER":"ngrok","PRIORITY":"4","_BOOT_ID":"488458ece6654edebf681e0a39e4836d","_CMDLINE":"/var/opt/cleep/modules/bin/ngrok/ngrok service run --config /var/opt/cleep/modules/bin/ngrok/ngrok.yml","_SYSTEMD_SLICE":"system.slice","SYSLOG_TIMESTAMP":"Mar 11 16:06:49 ","SYSLOG_RAW":"<4>Mar 11 16:06:49 ngrok[30994]: t=2025-03-11T16:06:49+0100 lvl=warn msg=\\"tunnel not found\\" pg=/api/tunnels/cleep id=febb4b78fc6556a0 name=cleep\\n","_SYSTEMD_CGROUP":"/system.slice/ngrok.service","_COMM":"ngrok","_GID":"0","_SOURCE_REALTIME_TIMESTAMP":"1741705609726794","_TRANSPORT":"syslog","_SYSTEMD_INVOCATION_ID":"b7dce7dfc8d045ffbeeff586c0c9948d","MESSAGE":"t=2025-03-11T16:06:49+0100 lvl=warn msg=\\"tunnel not found\\" pg=/api/tunnels/cleep id=febb4b78fc6556a0 name=cleep","_MACHINE_ID":"b563bb22f7e54d49995e5fdfa85aa167","_HOSTNAME":"cleepdev4","__REALTIME_TIMESTAMP":"1741705609728984","_UID":"0","_CAP_EFFECTIVE":"1ffffffffff","_EXE":"/var/opt/cleep/modules/bin/ngrok/ngrok","_PID":"30994","__MONOTONIC_TIMESTAMP":"9096419187400","SYSLOG_PID":"30994","__CURSOR":"s=dbd94044e5b74ede8cf84729bbadd466;i=1542ea;b=488458ece6654edebf681e0a39e4836d;m=845ecd59ac8;t=63012702bd3d8;x=e19b6357c96fdb31","_SYSTEMD_UNIT":"ngrok.service"}',
]


SYSTEMCTL_SHOW_OUTPUT = [
    "Type=simple",
    "Restart=always",
    "NotifyAccess=none",
    "RestartUSec=15s",
    "TimeoutStartUSec=1min 30s",
    "TimeoutStopUSec=1min 30s",
    "TimeoutAbortUSec=1min 30s",
    "TimeoutStartFailureMode=terminate",
    "TimeoutStopFailureMode=terminate",
    "RuntimeMaxUSec=infinity",
    "WatchdogUSec=0",
    "WatchdogTimestampMonotonic=0",
    "RootDirectoryStartOnly=no",
    "RemainAfterExit=no",
    "GuessMainPID=yes",
    "MainPID=30994",
    "ControlPID=0",
    "FileDescriptorStoreMax=0",
    "NFileDescriptorStore=0",
    "StatusErrno=0",
    "Result=success",
    "ReloadResult=success",
    "CleanResult=success",
    "UID=[not set]",
    "GID=[not set]",
    "NRestarts=0",
    "OOMPolicy=stop",
    "ExecMainStartTimestamp=Tue 2025-03-11 09:49:35 CET",
    "ExecMainStartTimestampMonotonic=9073784730299",
    "ExecMainExitTimestampMonotonic=0",
    "ExecMainPID=30994",
    "ExecMainCode=0",
    "ExecMainStatus=0",
    "ExecStart={ path=/var/opt/cleep/modules/bin/ngrok/ngrok ; argv[]=/var/opt/cleep/modules/bin/ngrok/ngrok service run --config /var/opt/cleep/modules/bin/ngrok/ngrok.yml ; ignore_errors=no ; start_time=[Tue 2025-03-11 09:49:35 CET] ; stop_time=[n/a] ; pid=30994 ; code=(null) ; status=0/0 }",
    "ExecStartEx={ path=/var/opt/cleep/modules/bin/ngrok/ngrok ; argv[]=/var/opt/cleep/modules/bin/ngrok/ngrok service run --config /var/opt/cleep/modules/bin/ngrok/ngrok.yml ; flags= ; start_time=[Tue 2025-03-11 09:49:35 CET] ; stop_time=[n/a] ; pid=30994 ; code=(null) ; status=0/0 }",
    "Slice=system.slice",
    "ControlGroup=/system.slice/ngrok.service",
    "MemoryCurrent=[not set]",
    "CPUUsageNSec=101988568000",
    "EffectiveCPUs=",
    "EffectiveMemoryNodes=",
    "TasksCurrent=9",
    "IPIngressBytes=[no data]",
    "IPIngressPackets=[no data]",
    "IPEgressBytes=[no data]",
    "IPEgressPackets=[no data]",
    "IOReadBytes=18446744073709551615",
    "IOReadOperations=18446744073709551615",
    "IOWriteBytes=18446744073709551615",
    "IOWriteOperations=18446744073709551615",
    "Delegate=no",
    "CPUAccounting=yes",
    "CPUWeight=[not set]",
    "StartupCPUWeight=[not set]",
    "CPUShares=[not set]",
    "StartupCPUShares=[not set]",
    "CPUQuotaPerSecUSec=infinity",
    "CPUQuotaPeriodUSec=infinity",
    "AllowedCPUs=",
    "AllowedMemoryNodes=",
    "IOAccounting=no",
    "IOWeight=[not set]",
    "StartupIOWeight=[not set]",
    "BlockIOAccounting=no",
    "BlockIOWeight=[not set]",
    "StartupBlockIOWeight=[not set]",
    "MemoryAccounting=yes",
    "DefaultMemoryLow=0",
    "DefaultMemoryMin=0",
    "MemoryMin=0",
    "MemoryLow=0",
    "MemoryHigh=infinity",
    "MemoryMax=infinity",
    "MemorySwapMax=infinity",
    "MemoryLimit=infinity",
    "DevicePolicy=auto",
    "TasksAccounting=yes",
    "TasksMax=2055",
    "IPAccounting=no",
    "ManagedOOMSwap=auto",
    "ManagedOOMMemoryPressure=auto",
    "ManagedOOMMemoryPressureLimitPercent=0%",
    "EnvironmentFiles=/etc/sysconfig/ngrok (ignore_errors=yes)",
    "UMask=0022",
    "LimitCPU=infinity",
    "LimitCPUSoft=infinity",
    "LimitFSIZE=infinity",
    "LimitFSIZESoft=infinity",
    "LimitDATA=infinity",
    "LimitDATASoft=infinity",
    "LimitSTACK=infinity",
    "LimitSTACKSoft=8388608",
    "LimitSTACKSoft=8388608",
    "LimitCORE=infinity",
    "LimitCORESoft=0",
    "LimitRSS=infinity",
    "LimitRSSSoft=infinity",
    "LimitNOFILE=524288",
    "LimitNOFILESoft=1024",
    "LimitAS=infinity",
    "LimitASSoft=infinity",
    "LimitNPROC=6850",
    "LimitNPROCSoft=6850",
    "LimitMEMLOCK=8388608",
    "LimitMEMLOCKSoft=8388608",
    "LimitLOCKS=infinity",
    "LimitLOCKSSoft=infinity",
    "LimitSIGPENDING=6850",
    "LimitSIGPENDINGSoft=6850",
    "LimitMSGQUEUE=819200",
    "LimitMSGQUEUESoft=819200",
    "LimitNICE=0",
    "LimitNICESoft=0",
    "LimitRTPRIO=0",
    "LimitRTPRIOSoft=0",
    "LimitRTTIME=infinity",
    "LimitRTTIMESoft=infinity",
    "RootHashSignature=",
    "OOMScoreAdjust=0",
    "CoredumpFilter=0x33",
    "Nice=0",
    "IOSchedulingClass=0",
    "IOSchedulingPriority=0",
    "CPUSchedulingPolicy=0",
    "CPUSchedulingPriority=0",
    "CPUAffinity=",
    "CPUAffinityFromNUMA=no",
    "NUMAPolicy=n/a",
    "NUMAMask=",
    "TimerSlackNSec=50000",
    "CPUSchedulingResetOnFork=no",
    "NonBlocking=no",
    "StandardInput=null",
    "StandardInputData=",
    "StandardOutput=journal",
    "StandardError=inherit",
    "TTYReset=no",
    "TTYVHangup=no",
    "TTYVTDisallocate=no",
    "LogLevelMax=-1",
    "LogRateLimitIntervalUSec=0",
    "LogRateLimitBurst=0",
    "SecureBits=0",
    "CapabilityBoundingSet=cap_chown cap_dac_override cap_dac_read_search cap_fowner cap_fsetid cap_kill cap_setgid cap_setuid cap_setpcap cap_linux_immutable cap_net_bind_service cap_net_broadcast cap_net_admin cap_net_raw cap_ipc_lock cap_ipc_owner cap_sys_module cap_sys_rawio cap_sys_chroot cap_sys_ptrace cap_sys_pacct cap_sys_admin cap_sys_boot cap_sys_nice cap_sys_resource cap_sys_time cap_sys_tty_config cap_mknod cap_lease cap_audit_write cap_audit_control cap_setfcap cap_mac_override cap_mac_admin cap_syslog cap_wake_alarm cap_block_suspend cap_audit_read cap_perfmon cap_bpf cap_checkpoint_restore",
    "AmbientCapabilities=",
    "DynamicUser=no",
    "RemoveIPC=no",
    "MountFlags=",
    "PrivateTmp=no",
    "PrivateDevices=no",
    "ProtectClock=no",
    "ProtectKernelTunables=no",
    "ProtectKernelModules=no",
    "ProtectKernelLogs=no",
    "ProtectControlGroups=no",
    "PrivateNetwork=no",
    "PrivateUsers=no",
    "PrivateMounts=no",
    "ProtectHome=no",
    "ProtectSystem=no",
    "SameProcessGroup=no",
    "UtmpMode=init",
    "IgnoreSIGPIPE=yes",
    "NoNewPrivileges=no",
    "SystemCallErrorNumber=2147483646",
    "LockPersonality=no",
    "RuntimeDirectoryPreserve=no",
    "RuntimeDirectoryMode=0755",
    "StateDirectoryMode=0755",
    "CacheDirectoryMode=0755",
    "LogsDirectoryMode=0755",
    "ConfigurationDirectoryMode=0755",
    "TimeoutCleanUSec=infinity",
    "MemoryDenyWriteExecute=no",
    "RestrictRealtime=no",
    "RestrictSUIDSGID=no",
    "RestrictNamespaces=no",
    "MountAPIVFS=no",
    "KeyringMode=private",
    "ProtectProc=default",
    "ProcSubset=all",
    "FinalKillSignal=9",
    "SendSIGKILL=yes",
    "SendSIGHUP=no",
    "WatchdogSignal=6",
    "Id=ngrok.service",
    "Names=ngrok.service",
    "Requires=system.slice sysinit.target",
    "WantedBy=multi-user.target",
    "Conflicts=shutdown.target",
    "Before=multi-user.target shutdown.target",
    "After=sysinit.target system.slice basic.target systemd-journald.socket",
    "Description=ngrok secure tunnel client",
    "LoadState=loaded",
    "ActiveState=active",
    "FreezerState=running",
    "SubState=running",
    "FragmentPath=/etc/systemd/system/ngrok.service",
    "UnitFileState=enabled",
    "UnitFilePreset=enabled",
    "StateChangeTimestamp=Tue 2025-03-11 09:49:35 CET",
    "StateChangeTimestampMonotonic=9073784732008",
    "InactiveExitTimestamp=Tue 2025-03-11 09:49:35 CET",
    "InactiveExitTimestampMonotonic=9073784732008",
    "ActiveEnterTimestamp=Tue 2025-03-11 09:49:35 CET",
    "ActiveEnterTimestampMonotonic=9073784732008",
    "ActiveExitTimestamp=Tue 2025-03-11 10:49:12 CET",
    "ActiveExitTimestampMonotonic=9073761912856",
    "InactiveEnterTimestamp=Tue 2025-03-11 09:49:12 CET",
    "InactiveEnterTimestampMonotonic=9073761923363",
    "CanStart=yes",
    "CanStop=yes",
    "CanReload=no",
    "CanIsolate=no",
    "CanFreeze=yes",
    "StopWhenUnneeded=no",
    "RefuseManualStart=no",
    "RefuseManualStop=no",
    "AllowIsolate=no",
    "DefaultDependencies=yes",
    "OnFailureJobMode=replace",
    "IgnoreOnIsolate=no",
    "NeedDaemonReload=no",
    "JobTimeoutUSec=infinity",
    "JobRunningTimeoutUSec=infinity",
    "JobTimeoutAction=none",
    "ConditionResult=yes",
    "AssertResult=yes",
    "ConditionTimestamp=Tue 2025-03-11 09:49:35 CET",
    "ConditionTimestampMonotonic=9073784696959",
    "AssertTimestamp=Tue 2025-03-11 09:49:35 CET",
    "AssertTimestampMonotonic=9073784697023",
    "Transient=no",
    "Perpetual=no",
    "StartLimitIntervalUSec=5s",
    "StartLimitBurst=10",
    "StartLimitAction=none",
    "FailureAction=none",
    "SuccessAction=none",
    "InvocationID=b7dce7dfc8d045ffbeeff586c0c9948d",
    "CollectMode=inactive",
]


class SystemctlTests(unittest.TestCase):
    def setUp(self):
        TestLib()
        logging.basicConfig(
            level=LOG_LEVEL, format="%(asctime)s %(name)s %(levelname)s : %(message)s"
        )
        self.lib = Systemctl()

    def tearDown(self):
        pass

    @patch("systemctl.datetime")
    def test_get_service_status_active(self, datetime_mock):
        datetime_mock.utcnow.return_value = datetime.datetime(2025, 3, 11, 14, 9, 35, 0)
        self.lib.command = Mock(
            return_value=self.__make_cmd_resp(stdout=SYSTEMCTL_SHOW_OUTPUT)
        )

        result = self.lib.get_service_status("service")
        logging.debug("Result: %s", result)

        self.assertDictEqual(
            result,
            {
                "state": "active",
                "substate": "running",
                "pid": 30994,
                "path": "/etc/systemd/system/ngrok.service",
                "start": datetime.datetime(2025, 3, 11, 9, 49, 35, tzinfo=tzlocal()),
                "stop": None,
                "restarts": 0,
                "runtime": 19200,
                "command": "/var/opt/cleep/modules/bin/ngrok/ngrok service run --config /var/opt/cleep/modules/bin/ngrok/ngrok.yml",
            },
        )
        self.lib.command.assert_called_with([AnyArg(), "show", "service"])

    @patch("systemctl.datetime")
    def test_get_service_status_inactive(self, datetime_mock):
        datetime_mock.utcnow.return_value = datetime.datetime(2025, 3, 11, 14, 9, 35, 0)
        systemctl_show_output = deepcopy(SYSTEMCTL_SHOW_OUTPUT)
        systemctl_show_output[194] = "ActiveState=inactive"
        systemctl_show_output[196] = "SubState=dead"
        self.lib.command = Mock(
            return_value=self.__make_cmd_resp(stdout=systemctl_show_output)
        )

        result = self.lib.get_service_status("service")
        logging.debug("Result: %s", result)

        self.assertDictEqual(
            result,
            {
                "state": "inactive",
                "substate": "dead",
                "pid": 30994,
                "path": "/etc/systemd/system/ngrok.service",
                "start": datetime.datetime(2025, 3, 11, 9, 49, 35, tzinfo=tzlocal()),
                "stop": datetime.datetime(2025, 3, 11, 10, 49, 12, tzinfo=tzlocal()),
                "restarts": 0,
                "runtime": 19200,
                "command": "/var/opt/cleep/modules/bin/ngrok/ngrok service run --config /var/opt/cleep/modules/bin/ngrok/ngrok.yml",
            },
        )
        self.lib.command.assert_called_with([AnyArg(), "show", "service"])

    def test_get_service_status_command_failed(self):
        self.lib.command = Mock(return_value=self.__make_cmd_resp(returncode=1))

        result = self.lib.get_service_status("service")
        logging.debug("Result: %s", result)

        self.assertIsNone(result)

    def test_start_service_success(self):
        self.lib.command = Mock(return_value=self.__make_cmd_resp())

        result = self.lib.start_service("service")

        self.assertTrue(result)
        self.lib.command.assert_called_with([AnyArg(), "start", "service"])

    def test_start_service_failure(self):
        self.lib.command = Mock(return_value=self.__make_cmd_resp(returncode=1))

        result = self.lib.start_service("service")

        self.assertFalse(result)
        self.lib.command.assert_called_with([AnyArg(), "start", "service"])

    def test_stop_service_success(self):
        self.lib.command = Mock(return_value=self.__make_cmd_resp())

        result = self.lib.stop_service("service")

        self.assertTrue(result)
        self.lib.command.assert_called_with([AnyArg(), "stop", "service"])

    def test_stop_service_failure(self):
        self.lib.command = Mock(return_value=self.__make_cmd_resp(returncode=1))

        result = self.lib.stop_service("service")

        self.assertFalse(result)
        self.lib.command.assert_called_with([AnyArg(), "stop", "service"])

    def test_restart_service_success(self):
        self.lib.command = Mock(return_value=self.__make_cmd_resp())

        result = self.lib.restart_service("service")

        self.assertTrue(result)
        self.lib.command.assert_called_with([AnyArg(), "restart", "service"])

    def test_restart_service_failure(self):
        self.lib.command = Mock(return_value=self.__make_cmd_resp(returncode=1))

        result = self.lib.restart_service("service")

        self.assertFalse(result)
        self.lib.command.assert_called_with([AnyArg(), "restart", "service"])

    def test_get_service_logs(self):
        self.lib.command = Mock(
            return_value=self.__make_cmd_resp(stdout=JOURNALCTL_OUTPUT)
        )

        result = self.lib.get_service_logs("service", minutes=10, lines=5, errors=True)
        logging.debug("Result: %s", result)

        self.assertListEqual(
            result,
            [
                (
                    datetime.datetime(2025, 3, 11, 16, 6, 51),
                    "warn",
                    't=2025-03-11T16:06:51+0100 lvl=warn msg="tunnel not found" pg=/api/tunnels/cleep id=df87d3495ef29edf name=cleep',
                ),
                (
                    datetime.datetime(2025, 3, 11, 16, 6, 51),
                    "info",
                    "t=2025-03-11T16:06:51+0100 lvl=info msg=end pg=/api/tunnels/cleep id=df87d3495ef29edf status=404 dur=896.662µs",
                ),
                (
                    datetime.datetime(2025, 3, 11, 16, 6, 51),
                    "info",
                    't=2025-03-11T16:06:51+0100 lvl=warn msg="tunnel not found" pg=/api/tunnels/cleep id=df87d3495ef29edf name=cleep',
                ),
                (
                    datetime.datetime(2025, 3, 11, 16, 6, 51),
                    "info",
                    "t=2025-03-11T16:06:51+0100 lvl=info msg=start pg=/api/tunnels/cleep id=df87d3495ef29edf",
                ),
                (
                    datetime.datetime(2025, 3, 11, 16, 6, 49),
                    "warn",
                    't=2025-03-11T16:06:49+0100 lvl=warn msg="tunnel not found" pg=/api/tunnels/cleep id=febb4b78fc6556a0 name=cleep',
                ),
            ],
        )
        self.lib.command.assert_called_with(
            [
                AnyArg(),
                "-u",
                "service",
                "--no-pager",
                "--since",
                "10 minutes ago",
                "-r",
                "--quiet",
                "-o",
                "json",
                "-n",
                "5",
                "-p",
                "3",
            ]
        )

    def test_get_service_logs_command_failed(self):
        self.lib.command = Mock(
            return_value=self.__make_cmd_resp(returncode=1)
        )

        result = self.lib.get_service_logs("service", minutes=10, lines=5, errors=True)
        logging.debug("Result: %s", result)

        self.assertIsNone(result)

    def test_get_service_logs_invalid_stdout(self):
        self.lib.command = Mock(
            return_value=self.__make_cmd_resp(stdout=["hello world"])
        )

        result = self.lib.get_service_logs("service", minutes=10, lines=5, errors=True)
        logging.debug("Result: %s", result)

        self.assertIsNone(result)

    def test__parse_datetime_failure(self):
        result = self.lib._Systemctl__parse_datetime("hello world")

        self.assertIsNone(result)

    def test__parse_datetime_default_value(self):
        result = self.lib._Systemctl__parse_datetime("hello world", "default")

        self.assertEqual(result, "default")

    def test__parse_integer_failure(self):
        result = self.lib._Systemctl__parse_integer("hello world")

        self.assertEqual(result, 0)

    def test__parse_show_stdout_failure(self):
        result = self.lib._Systemctl__parse_show_stdout([123456])

        self.assertDictEqual(result, {})

    def test__parse_execstart_field_failure(self):
        result = self.lib._Systemctl__parse_execstart_field("something")

        self.assertDictEqual(result, {})

    def __make_cmd_resp(
        self, stdout=[], returncode=0, stderr=[], error=False, killed=False
    ):
        return {
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr,
            "error": error,
            "killed": killed,
        }


if __name__ == "__main__":
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_systemctl.py; coverage report -m -i
    unittest.main()
