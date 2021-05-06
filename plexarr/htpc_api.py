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

    def getMovieDownloads(self):
        """List all downloaded movies that need to be imported into Radarr

        Returns:
            movies (list) - The remote paths of the downloaded movies
        """
        host = dict(self.mal.items())
        with SSHClient() as ssh:
            ssh.load_system_host_keys()
            ssh.connect(hostname=host['ip'], port=host['port'], username=host['username'])
            ftp = ssh.open_sftp()
            return [os.path.join(host['movies'], movie) for movie in ftp.listdir(host['movies'])]

    def getSeriesDownloads(self):
        """List all downloaded series that need to be imported into Radarr

        Returns:
            series (list) - The remote paths of the downloaded series
        """
        host = dict(self.mal.items())
        with SSHClient() as ssh:
            ssh.load_system_host_keys()
            ssh.connect(hostname=host['ip'], port=host['port'], username=host['username'])
            ftp = ssh.open_sftp()
            return [os.path.join(host['series'], series) for series in ftp.listdir(host['series'])]

    def getSeasonDownloads(self, series=''):
        """List all downloaded seasons for a given series that need to be imported into Radarr

        Requires:
            series (string) - The title of the TV Series (ex: "Bar Rescue")
        Returns:
            seasons (list) - The remote paths of the downloaded seasons
        """
        host = dict(self.mal.items())
        series_path = os.path.join(host['series'], series)
        with SSHClient() as ssh:
            ssh.load_system_host_keys()
            ssh.connect(hostname=host['ip'], port=host['port'], username=host['username'])
            ftp = ssh.open_sftp()
            return [os.path.join(series_path, season) for season in ftp.listdir(series_path)]

    def getEpisodeDownloads(self, series='', season=''):
        """List all downloaded episodes for a given series and season that need to be imported into Radarr

        Requires:
            series (string) - The title of the TV Series (ex: "Bar Rescue")
        Returns:
            episodes (list) - The remote paths of the downloaded episodes
        """
        host = dict(self.mal.items())
        season_path = os.path.join(host['series'], series, season)
        with SSHClient() as ssh:
            ssh.load_system_host_keys()
            ssh.connect(hostname=host['ip'], port=host['port'], username=host['username'])
            ftp = ssh.open_sftp()
            return [os.path.join(season_path, episode) for episode in ftp.listdir(season_path)]

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

