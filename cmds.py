import re
from datetime import datetime
from getpass import getpass

import progressbar
from colors import green, red
from novaclient import exceptions
from tabulate import tabulate

import ssh
from errors import CommandExecutionError, InvalidCommandArgs
from nova_wrapper import NovaWrapper


class AbstractCommand(object):
    min_args = 0
    needs_auth = True

    def execute(self, *args):
        self.valid_args(args)
        self.flags = self.extract_flags(args)
        self.nova = NovaWrapper() if self.needs_auth else None
        self.run(*args)

    def valid_args(self, args):
        if len(args) < self.min_args:
            msg = red("Too few arguments. {} Required.".format(self.min_args))
            raise InvalidCommandArgs(msg)

    def run(self, *args):
        """Override this method in inherting class."""
        pass

    def extract_flags(self, args):
        flags = {}
        for arg in args:
            if re.match(".*?=.*", arg):
                index = arg.index('=')
                flags[arg[:index].strip('-')] = arg[index+1:]
        return flags

    def ssh_connect(self, server):
        user = self.flags.get('user')
        host = self.nova.floating_ip(server)
        try:
            port = int(self.flags.get('port', 22))
        except ValueError:
            port = 22
        print "Connecting to {}@{} -p {}".format(user, host, port)
        conn = ssh.Connection(host, username=user, port=port)
        return conn

    def remote_command(self, cmds, *args):
        if not isinstance(cmds, list):
            cmds = [cmds]
        target = args[0]
        server = self.nova.server(target)
        conn = self.ssh_connect(server)
        pword = getpass("Enter sudo password: ")
        for cmd in cmds:
            print "Executing: {}".format(cmd)
            cmd = "echo {} | sudo -S {}".format(pword, cmd)
            conn.execute(cmd)


class List(AbstractCommand):
    """Lists instances in the current tenant."""
    def run(self, *args):
        for server in self.nova.servers():
            # TODO: Add the IPs of each instance.
            if server.status == u"ACTIVE":
                print green(server.name)
            else:
                print red(server.name)


class Images(AbstractCommand):
    """Lists all available images."""

    def run(self, *args):
        print tabulate([self.nova.image_data(i) for i in self.nova.images()])

class Clone(AbstractCommand):
    """Clone an instance in the current tenant."""
    min_args = 2

    def run(self, *args):
        server = self.nova.server(args[0])
        clone = self.nova.clone(server, args[1])
        self.nova.print_server(clone)
        print green("Success!")


class Desalt(AbstractCommand):
    """Turns off salt minion. [--user, --port]."""
    min_args = 1

    def run(self, *args):
        self.remote_command("service salt-minion stop", *args)


class Emancipate(AbstractCommand):
    """Turns slave mysql server to master, removes read-only. [--user, --port, --dbuser]."""
    min_args = 1

    def run(self, *args):
        msg = "Are you sure you want to emancipate? This is unreversable? Y/n "
        if raw_input(msg) == "Y":
            dbuser = self.flags.get('dbuser', '')
            cmds = [
                "sed -i 's/read-only//g' /etc/mysql/my.cnf",
                'mysql -u {} -e "stop slave;"'.format(dbuser),
            ]
            self.remote_command(cmds, *args)
