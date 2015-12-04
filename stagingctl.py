import sys

from tabulate import tabulate
from novaclient.exceptions import AuthorizationFailure, Unauthorized

from cmds import Clone, Images, List, Desalt, Emancipate
from colors import red

from errors import (
    CommandExecutionError,
    ConnectionFailure,
    InvalidCommandArgs,
    WrapperFailure,
)


CMDS = {
    'clone': Clone,
    'de-salt': Desalt,
    'emancipate': Emancipate,
    'images': Images,
    'list': List,
}


def fetch_command(cmd):
    if cmd == "--help":
        print "usage: stagingctl [--help] <command> [<args>]\n"
        print tabulate([[name, cmd.__doc__ ] for name, cmd in CMDS.iteritems()])
    elif cmd in CMDS:
        return CMDS[cmd]()
    else:
        print red("'{}' is not a valid command.".format(cmd))


def main():
    args = sys.argv[1:]
    cmd = fetch_command(args.pop(0))
    errors = (InvalidCommandArgs, CommandExecutionError,
              ConnectionFailure, WrapperFailure)
    try:
        cmd.execute(*args)
    except AttributeError:
        pass
    except (AuthorizationFailure, Unauthorized):
        print red("Authentication Failed!")
        print "Did you 'source TENANT_NAME.openrc.sh' with a valid password?"
    except errors as e:
        print e.message


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main()
