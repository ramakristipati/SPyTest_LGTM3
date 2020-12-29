import argparse

max_time_default = {"reboot":0, "port":300, "session":0, "module":1200, "function" : 600}

max_time_help_msg = """
    Maximum time for various operations.
        <reboot>: Wait time in seconds for ports to come up after reboot default {} seconds
        <port>: time for ports to comeup default {} seconds
        <session>: time for session init to complete default {} seconds
        <module>: time for session module to complete default {} seconds
        <function>: time for session function to complete default {} seconds
    """.format(max_time_default["reboot"], max_time_default["port"], max_time_default["session"],
               max_time_default["module"], max_time_default["function"])

arg_defaults = {
  "--ignore-tcmap-errors": 0,
  "--tclist-map": None,
  "--tclist-bucket": None,
  "--tclist-file": [],
  "--tclist-file-exclude": [],
  "--tclist-csv": [],
  "--tclist-csv-exclude": [],
  "--logs-path": None,
  "--file-mode": False,
  "--quick-test": False,
  "--email": None,
  "--email-subject": "Run Report",
  "--email-attachments": 0,
  "--skip-tgen": False,
  "--tgen-module-init": 1,
  "--topology-check": ["module"],
  "--load-config-method": "none",
  "--skip-init-config": False,
  "--skip-load-config": "module",
  "--load-image": "onie",
  "--skip-verify-config": "none",
  "--ignore-dep-check": 0,
  "--memory-check": "none",
  "--syslog-check": "err",
  "--save-sairedis": "none",
  "--faster-init": 1,
  "--faster-cli": 1,
  "--fetch-core-files": "session",
  "--get-tech-support": "onfail-epilog",
  "--reboot-wait": max_time_default["reboot"],
  "--port-init-wait": max_time_default["port"],
  "--tc-max-timeout": max_time_default["function"],
  "--module-init-max-timeout": max_time_default["module"],
  "--max-time reboot": max_time_default["reboot"],
  "--max-time port": max_time_default["port"],
  "--max-time function": max_time_default["function"],
  "--max-time module": max_time_default["module"],
  "--max-time session": max_time_default["session"],
  "--results-prefix": None,
  "--results-compare": None,
  "--exclude-devices": None,
  "--include-devices": None,
  "--run-progress-report": 0,
  "--env": {},
  "--random-order": 1,
  "--repeat-test": ["", 1],
  "--rps-reboot": None,
  "--pde": False,
  "--community-build": "none",
  "--tryssh": 0,
  "--first-test-only": False,
  "--config-profile": None,
  "--build-url": None,
  "--libsai-url": None,
  "--clear-tech-support": 0,
  "--module-epilog-tgen-cleanup": 1,
  "--module-epilog": 1,
  "--graceful-exit": 1,
  "--reuse-results": "none",
  "--link-param": [],
  "--dev-prop": [],
  "--dev-param": [],
  "--change-section": [],
  "--ixserver": [],
  "--ui-type": "click",
  "--breakout-mode": "native",
  "--speed-mode": "configured",
  "--ifname-type": "native",
  "--mgmt-vrf": 0
}

def get_default(name, default):
    if name in arg_defaults:
        return arg_defaults[name]
    return default

def get_default_all():
    return sorted(arg_defaults.items())

def validate_repeat():
    class ArgValidateRepeat(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            message = ''
            types_supported = ["function", "module"]
            if len(values) != 2:
                message = "requires both <type> and <times>"
            elif values[0] not in types_supported:
                message = "<type> should be one of {}".format(types_supported)
            else:
                try:
                    values[1] = int(values[1])
                except ValueError:
                    message = "<times> should be integer"
            if message:
                raise argparse.ArgumentError(self, message)
            setattr(namespace, self.dest, values)
    return ArgValidateRepeat

def validate_exec_phase(exec_phases):
    class ArgValidateExecPhase(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            for value in values.split(","):
                if value not in exec_phases:
                    message = "unknown sub-option {}".format(value)
                    raise argparse.ArgumentError(self, message)
            setattr(namespace, self.dest, values)
    return ArgValidateExecPhase

def validate_env():
    class ArgValidateEnv(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            help1 = "requires <name> and <value>"
            help1 = help1 + "seperated by '=' or space"
            if len(values) > 2:
                raise argparse.ArgumentError(self, help1)
            if len(values) == 1:
                values = values[0].split('=')
            if len(values) != 2:
                raise argparse.ArgumentError(self, help1)
            getattr(namespace, self.dest).update({values[0]:values[1]})
    return ArgValidateEnv

def validate_max_time():
    class ArgValidateMaxTime(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            options = ['port', 'session', "module", "function"]
            help1 = "requires <type> and <time> where type: {}".format(options)
            help1 = help1 + "seperated by '=' or space"
            help2 = "<type> should be one of {}".format(options)
            help3 = "<time> should be integer"
            if len(values) > 2:
                raise argparse.ArgumentError(self, help1)
            if len(values) == 1:
                values = values[0].split('=')
            if len(values) != 2:
                raise argparse.ArgumentError(self, help1)
            if values[0] not in options:
                raise argparse.ArgumentError(self, help2)
            try:
                values[1] = int(values[1])
            except ValueError:
                raise argparse.ArgumentError(self, help3)
            getattr(namespace, self.dest).update({values[0]:values[1]})
    return ArgValidateMaxTime

class HelpFormatter(argparse.HelpFormatter):
    def _format_action(self, action):
        if type(action).__name__ in ["ArgValidateEnv", "ArgValidateMaxTime"]:
            action.nargs=1
        if type(action) == argparse._SubParsersAction:
            # inject new class variable for subcommand formatting
            subactions = action._get_subactions()
            invocations = [self._format_action_invocation(a) for a in subactions]
            self._subcommand_max_length = max(len(i) for i in invocations)

        if type(action) == argparse._SubParsersAction._ChoicesPseudoAction:
            # format subcommand help line
            subcommand = self._format_action_invocation(action) # type: str
            width = self._subcommand_max_length
            help_text = ""
            if action.help:
                help_text = self._expand_help(action)
            return "  {:{width}} -  {}\n".format(subcommand, help_text, width=width)

        elif type(action) == argparse._SubParsersAction:
            # process subcommand help section
            msg = '\n'
            for subaction in action._get_subactions():
                msg += self._format_action(subaction)
            return msg
        else:
            return super(HelpFormatter, self)._format_action(action)

