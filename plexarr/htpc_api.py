# -- sys utils -- #
from configparser import ConfigParser
from pathlib import Path
import subprocess
import sys
import os

# -- video utils -- #
from pymediainfo import MediaInfo

# -- network utils -- #
# import wget
# import markdown
from paramiko import SSHClient, AutoAddPolicy
from scp import SCPClient
import tldextract
import netifaces
import socket


def progress4(filename, size, sent, peername):
    if isinstance(filename, bytes):
        filename = filename.decode()
    sys.stdout.write("(%s:%s) %s\'s progress: %.2f%%   \r" % (peername[0], peername[1], filename, float(sent)/float(size)*100))


def getNetHost():
    dns_domain = socket.getfqdn(netifaces.gateways()["default"][2][0])
    tld_extract = tldextract.TLDExtract(
        suffix_list_urls=["https://proxy.hopto.org/suffixes"],
        cache_dir="/tmp/",
        fallback_to_snapshot=False,
    )
    net_info = tld_extract(dns_domain)
    net_host = f'{net_info.domain}.{net_info.suffix}'           # udel.edu, windy.pickle
    return net_host


class HTPC_API(object):
    """Wrapper for htpc_api (Your Home Theater System)"""
    def __init__(self):
        """Init Constructor

        From config:
            imac (object): Server Details
            mal (object): Server Details
            og (object): Server Details
        """
        config = ConfigParser()
        config.read(os.path.join(os.path.expanduser('~'), '.config', 'plexarr.ini'))
        self.jump = config['jump']
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

    def getMusicVideoArtists(self):
        """List all Artists in the Music Videos directory

        Returns:
            artist (list) - The remote paths of the music video artists
        """
        host = dict(self.imac.items())
        with SSHClient() as ssh:
            ssh.load_system_host_keys()
            ssh.connect(hostname=host['ip'], port=host['port'], username=host['username'])
            sftp = ssh.open_sftp()
            return [artist for artist in sftp.listdir(host['music_videos'])]

    def getMusicVideos(self, artist=''):
        """List all Music Videos belonging to an Artists

        Returns:
            music_videos (list) - The remote file path of the Artist's Music Videos
        """
        host = dict(self.imac.items())
        artist_path = os.path.join(host['music_videos'], artist)
        with SSHClient() as ssh:
            ssh.load_system_host_keys()
            ssh.connect(hostname=host['ip'], port=host['port'], username=host['username'])
            sftp = ssh.open_sftp()
            return [os.path.join(artist_path, video_file) for video_file in sftp.listdir(artist_path)]

    def downloadMusicVideo(self, video_file=''):
        """Download the remote Music Video file for parsing

        Returns:
            music_video (FILE OBJECT) - FILE object pointing to the music video that can be opened and read
        """
        # -- https://stackoverflow.com/questions/58433996/reading-file-opened-with-python-paramiko-sftpclient-open-method-is-slow
        host = dict(self.imac.items())
        local_path = Path.cwd().joinpath('tmp').as_posix()
        temp_file = Path(local_path).joinpath(Path(video_file).parts[-1]).as_posix()

        with SSHClient() as ssh:
            ssh.load_system_host_keys()
            ssh.connect(hostname=host['ip'], port=host['port'], username=host['username'])

            with SCPClient(ssh.get_transport(), progress4=progress4) as scp:
                scp.get(remote_path=video_file, local_path=temp_file)
        return temp_file

    def uploadMovie(self, folder=''):
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

    def uploadSeries(self, folder='', host={}):
        """Upload series directory containing episode files to host["mal"]

        Args:
            Requires - folder (str)  - The local path of the downloaded series
            Optional - host (dict) - object contain remote host network info
        Returns:
            series_path (str) - The remote path of the uploaded series (folder)
        """
        host = dict(self.mal.items()) if not host else host

        with SSHClient() as ssh:
            ssh.load_system_host_keys()
            ssh.connect(hostname=host['ip'], port=host['port'], username=host['username'])
            with SCPClient(ssh.get_transport(), progress4=progress4) as scp:
                scp.put(files=folder, remote_path=host['series'], recursive=True)
        return os.path.join(host['series'], os.path.split(folder)[1])

    def uploadYouTubeSeries(self, folder=''):
        """Upload YouTube series folder containing episode files to host["imac"]

        Args:
            Requires - folder (str)  - The local path of the downloaded series
        Returns:
            series_path (str) - The remote path of the uploaded series (folder)
        """
        jump = dict(self.jump.items())
        imac = dict(self.imac.items())
        vm_channel = None
        net_host = getNetHost()
        print(f'HOST NETWORK: "{net_host}"')

        # -- NEED TO USE JUMP HOST ??? -- #
        if "windy.pickle" not in net_host:
            print(f' + jump host: {jump}')
            ssh_jump = SSHClient()
            ssh_jump.load_system_host_keys()
            ssh_jump.connect(hostname=jump["host"], port=jump["port"], username=jump["username"])

            vm_transport = ssh_jump.get_transport()
            dest_addr = (imac["ip"], int(imac["port"]))
            local_addr = (jump["host"], int(jump["port"]))
            vm_channel = vm_transport.open_channel("direct-tcpip", dest_addr, local_addr)

        # -- TRANSFER TO IMAC -- #
        print(f' + dest host: {imac}')
        with SSHClient() as ssh_imac:
            # -- ssh_imac.set_missing_host_key_policy(AutoAddPolicy())
            ssh_imac.load_system_host_keys()
            ssh_imac.connect(hostname=imac["ip"], port=imac["port"], username=imac["username"], sock=vm_channel)
            with SCPClient(ssh_imac.get_transport(), progress4=progress4) as scp:
                scp.put(files=folder, remote_path=imac['yt_series'], recursive=True)

        # -- CLOSE JUMP HOST CONNECTION IF USED -- #
        ssh_jump.close() if vm_channel else None

        return str(Path(imac['yt_series'], Path(folder).name))

    def uploadIPTV(self, fname):
        """Upload XML TV-Guide or M3U playlist file to host["mal"]

        Args:
            Requires - folder (str) - The local file path of XML or M3U file
        Returns:
            file_path (str) - The remote path of the uploaded XML or M3U file
        """
        host = dict(self.imac.items())
        with SSHClient() as ssh:
            ssh.load_system_host_keys()
            ssh.connect(hostname=host['ip'], port=host['port'], username=host['username'])
            with SCPClient(ssh.get_transport(), progress4=progress4) as scp:
                scp.put(files=fname, remote_path=host['iptv'], recursive=False)
        return os.path.join(host['iptv'], os.path.split(fname)[1])

    def runCommand(self, cmd, host='imac'):
        """Run a shell command over ssh

        Args:
            Requires - cmd (str) - the command to run
        Returns:
            std_out (str) - The output of the command
        """

        if host == 'imac':
            host = dict(self.imac.items())
        elif host == 'mal':
            host = dict(self.mal.items())
        elif host == 'og':
            host = dict(self.og.items())

        # path = f'/Users/{host["username"]}/bin/{cmd}'
        path = f'{cmd}'
        ssh_cmd = f'ssh -t -p {host["port"]} {host["username"]}@{host["ip"]} \'{path}\''
        output = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True).stdout.strip()
        # return markdown.markdown(''.join([f"    {l}\n" for l in output.splitlines()]))
        return output
