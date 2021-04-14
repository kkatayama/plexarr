from configparser import ConfigParser
from paramiko import SSHClient
from scp import SCPClient
import sys
import os


def progress4(filename, size, sent, peername):
    sys.stdout.write("(%s:%s) %s\'s progress: %.2f%%   \r" % (peername[0], peername[1], filename, float(sent)/float(size)*100) )


class HTPC_API(object):
    """Wrapper for htpc_api (Your Home Theater System)
    """
    def __init__(self):
        """Constructor

        From config:
            imac (object): Server Details
            mal (object): Server Details
            og (object): Server Details
        """
        config = ConfigParser()
        config.read(os.path.join(os.path.expanduser('~'), '.config', 'plexarr.ini'))
        self.imac = config['imac']
        self.mal = config['mal']
        self.og = config['og']

    def uploadMovie(self, folder):
        """Upload movie directory containing movie file to host["mal"]

        Args:
            Requires - folder (str)  - The local path of the downloaded movie
        Returns:
            movie_path (str) - The remote path of the uploaded movie (folder)
        """
        host = dict(self.mal.items())
        with SSHClient() as ssh:
            ssh.load_system_host_keys()
            ssh.connect(hostname=host['ip'], port=host['port'], username=host['username'])
            with SCPClient(ssh.get_transport(), progress4=progress4) as scp:
                scp.put(files=folder, remote_path=host['movies'], recursive=True)
        return os.path.join(host['movies'], os.path.split(folder)[1])

    def uploadSeries(self, folder):
        """Upload movie directory containing movie file to host["mal"]

        Args:
            Requires - folder (str)  - The local path of the downloaded movie
        Returns:
            movie_path (str) - The remote path of the uploaded movie (folder)
        """
        host = dict(self.mal.items())
        with SSHClient() as ssh:
            ssh.load_system_host_keys()
            ssh.connect(hostname=host['ip'], port=host['port'], username=host['username'])
            with SCPClient(ssh.get_transport(), progress4=progress4) as scp:
                scp.put(files=folder, remote_path=host['series'], recursive=True)
        return os.path.join(host['series'], os.path.split(folder)[1])

