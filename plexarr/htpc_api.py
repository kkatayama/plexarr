from configparser import ConfigParser
from paramiko import SSHClient
from scp import SCPClient
import os


class HTPC_API(object):
    """Wrapper for htpc_api (Your Home Theater System)
    """
    def __init__(self):
        """Constructor"""
        config = ConfigParser()
        config.read(os.path.join(os.path.expanduser('~'), '.config', 'plexarr.ini'))
        self.imac = config['imac']
        self.mal = config['mal']
        self.og = config['og']
        
