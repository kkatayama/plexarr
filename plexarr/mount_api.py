import os
import shutil
import subprocess
from configparser import ConfigParser
from pathlib import Path

from furl import furl
from pymediainfo import MediaInfo
from rich import print
from sh import sudo
from teddy import find_cmd, process_handbrake_output


class MountAPI(object):
    """Wrapper for sh.mount()
    """
    def __init__(self, machine="", volume=""):
        """Constructor
        """
        config = ConfigParser()
        config.read(Path(Path.home(), ".config", "plexarr.ini"))
        config.read(os.path.join(os.path.expanduser('~'), '.config', 'plexarr.ini'))

        self.mount_path = config["macbook"].get('mount_path')
        self.artists_path = config["macbook"].get('artists_path')
        self.library_path = config["macbook"].get('library_path')
        self.temp_source = config["macbook"].get('temp_source')
        self.temp_output = config["macbook"].get('temp_output')
        self.machine = machine
        self.volume = volume

        if ((machine) and (volume)):
            self.ip = config[machine].get('ip')
            self.mountDrive()

    def checkMount(self, mount_path):
        """checkMount
        """
        if mount_path:
            self.mount_path = mount_path
        else:
            mount_path = self.mount_path
        return os.path.ismount(mount_path)

    def mountDrive(self, mount_path=''):
        if mount_path:
            self.mount_path = mount_path
        else:
            mount_path = self.mount_path

        if not self.checkMount(mount_path=mount_path):
            print(f'[yellow]"{mount_path}": NOT MOUNTED![/yellow]')
            sudo.mkdir(mount_path)
            # "soft,intr,rsize=8192,wsize=8192,timeo=900,retrans=3,proto=tcp",
            sudo.mount(
                "-t",
                "nfs",
                "-o",
                "soft,intr,resvport,rw",
                f"{self.ip}:{self.volume}",
                f"{mount_path}",
            )
        print(f'[green]"{mount_path}: MOUNTED :)[/green]')

    def unmountDrive(self, mount_path=''):
        if mount_path:
            self.mount_path = mount_path
        else:
            mount_path = self.mount_path

        if self.checkMount(mount_path=mount_path):
            sudo.umount("-h", f"{self.ip}")
            print(f'[green]"{mount_path}": UNMOUNTED[/green]')

    def getArtists(self):
        return (artist.parts[-1] for artist in Path(self.artists_path).iterdir() if (artist.is_dir()))

    def getArtistVideos(self, artist=''):
        artist_path = Path(self.artists_path).joinpath(artist)
        return (v_file for v_file in artist_path.iterdir() if (v_file.is_file() and v_file.name != ".DS_STORE"))

    def scanVideo(self, video_file=''):
        info = MediaInfo.parse(video_file)
        media = next((t.to_data() for t in info.tracks if t.track_type == "General"), None)
        video = next((t.to_data() for t in info.tracks if t.track_type == "Video"), None)
        audio = next((t.to_data() for t in info.tracks if t.track_type == "Audio"), None)

        if media.get("comment"):
            media = {key: media.get(key) for key in ["file_name", "file_extension", "file_size", "comment", "duration", "overall_bit_rate", "frame_rate"]}
        else:
            media = {key: media.get(key) for key in ["file_name", "file_extension", "file_size", "duration", "overall_bit_rate", "frame_rate"]}
        video = {key: video.get(key) for key in ["codec_id", "stream_size", "width", "height", "duration", "bit_rate", "frame_rate"]}
        audio = {key: audio.get(key) for key in ["codec_id", "stream_size", "duration", "sampling_rate", "bit_rate"]}

        # for track in [media, video, audio]:
        #     c.print(track)
        return media, video, audio

    def copyVideo(self, source='', destination=''):
        if not destination:
            destination = Path(self.temp_source).joinpath(Path(source).name)
            self.temp_video_source = destination
        print('[green]copying...[/green]')
        print(f'[cyan]source[/cyan]: "{source}"')
        print(f'[cyan]output[/cyan]: "{destination}"')
        return shutil.copy2(source, destination)

    def convertVideo(self, source_file='', output_file='', preset=''):
        if not source_file:
            source_file = self.temp_video_source
        source_file = Path(source_file)
        if not output_file:
            output_file = Path(self.temp_output).joinpath(source_file.name)
        output_file = Path(output_file)
        self.temp_video_output = output_file
        print(f'[yellow]converting video[/yellow]: "{output_file.name}"')

        HandBrakeCLI = find_cmd('handbrakecli')
        if not preset:
            preset = 'Very Fast 1080p30'
        cmd = [
            HandBrakeCLI,
            '-i', '{}'.format(source_file),
            '-o', '{}'.format(output_file),
            '-Z', '{}'.format(preset),
            '-O', '--all-subtitles', '--subtitle-lang-list', 'eng'
        ]
        print(' '.join(cmd))
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        process_handbrake_output(p)
        retcode = p.wait()
        if retcode != 0:
            raise subprocess.CalledProcessError(retcode, cmd)

        # print('RETURN CODE: {}'.format(p.wait()))
        print('[magenta]conversion finished...[/magenta]')
        return output_file


