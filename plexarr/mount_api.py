import os
import shutil
from configparser import ConfigParser
from pathlib import Path

from pymediainfo import MediaInfo
from rich import print
from sh import mount, sudo, umount


class MountAPI(object):
    """Wrapper for sh.mount()
    """
    def __init__(self, machine: str, volume: str):
        """Constructor
        """
        config = ConfigParser()
        config.read(os.path.join(os.path.expanduser('~'), '.config', 'plexarr.ini'))

        self.volume = volume
        self.ip = config[machine].get('ip')
        self.mount_path = config["macbook"].get('mount_path')
        self.artists_path = config["macbook"].get('artists_path')
        self.temp_path = config["macbook"].get('temp_path')
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
            sudo.mount(
                "-t",
                "nfs",
                "-o",
                "soft,intr,resvport,rw",
                f"{self.ip}:{self.volume}",
                "/Users/katayama/Documents/Fun/nfs/mac_share",
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

        media = {key: media[key] for key in ["file_name", "file_extension", "file_size", "duration", "overall_bit_rate", "frame_rate"]}
        video = {key: video[key] for key in ["codec_id", "stream_size", "width", "height", "duration", "bit_rate", "frame_rate"]}
        audio = {key: audio[key] for key in ["codec_id", "stream_size", "duration", "sampling_rate", "bit_rate"]}

        # for track in [media, video, audio]:
        #     c.print(track)
        return media, video, audio

    def copyVideo(self, video_file=''):
        vid
