from rich.progress import Progress
from rich import print
from configparser import ConfigParser
import youtube_dl
import shutil
import os


class MyLogger(object):
    def info(self, msg):
        print(msg)

    def debug(self, msg):
        # print(msg)
        pass

    def warning(self, msg):
        # print(msg)
        pass

    def error(self, msg):
        # print(msg)
        pass

class YouTubeAPI(object):
    """Wrapper for YouTubeAPI via youtube_dl
    """
    def __init__(self):
        """Constructor requires API-KEY

        From config:
            cookies (str): Path to Cookies File
        """
        config = ConfigParser()
        config.read(os.path.join(os.path.expanduser('~'), '.config', 'plexarr.ini'))

        self.path = config['youtube'].get('path')
        self.cookies = config['youtube'].get('cookies')
        self.progress = Progress()
        self.task = None
        self.downloaded_bytes = 0
        self.download_status = False


    # -- https://stackoverflow.com/a/58667850/3370913
    def my_hook(self, d):
        # print(d)
        if d['status'] == 'finished':
            self.progress.stop()
            file_tuple = os.path.split(os.path.abspath(d['filename']))
            print(f'Done downloading "{file_tuple[1]}"')
        if d['status'] == 'downloading':
            if not self.download_status:
                try:
                    total = int(d["total_bytes"])
                except:
                    total = int(d["total_bytes_estimate"])
                self.download_status = True
                self.task = self.progress.add_task("[cyan]Downloading...", total=total)
                self.progress.start()
            step = int(d["downloaded_bytes"]) - int(self.downloaded_bytes)
            self.downloaded_bytes = int(d["downloaded_bytes"])
            self.progress.update(self.task, advance=step)
            # print(d['filename'], d['_percent_str'], d['_eta_str'])


    def downloadMovie(self, title: str, video_url: str):
        """Downlod YouTube video into folder

        Args:
            Requires - folder (str) - The video title to store the downloaded video
            Requires - video_url (str) - The link of the YouTube video
        """
        # -- setting up path configs
        self.title = title
        self.folder = os.path.join(self.path, title)
        self.f_name = os.path.join(self.path, title, f'{title}.mp4')
        self.video_url_path = os.path.join(self.path, title, 'video_url.txt')

        # -- backup video_url and remove stale directories
        if os.path.exists(self.folder):
            if os.path.exists(self.video_url_path):
                print(f'importing video_url from [magenta]{self.video_url_path}[/magenta]')
                with open(self.video_url_path) as f:
                    video_url = f.readline()
            print(f'deleting existing directory: "{self.folder}"')
            shutil.rmtree(self.folder)

        # -- create fresh directory and backup video_url
        print(f'creating directory: "{self.folder}"')
        print(f'exporting video_url to [magenta]"video_url.txt"[/magenta]')
        print(f'{{"video_url": {video_url}}}')
        os.mkdir(self.folder)
        with open(self.video_url_path, 'w') as f:
            f.write(f'{video_url}\n')

        ### Download Movie via YoutubeDL ###
        ytdl_opts = {
            'writesubtitles': True,
            'subtitle': '--write-sub --sub-lang en',
            'cookiefile': self.cookies,
            'format': "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            'outtmpl': self.f_name,
            'postprocessors': [{
                'key': 'FFmpegEmbedSubtitle'
            }],
            'logger': MyLogger(),
            'progress_hooks': [self.my_hook]
        }
        with youtube_dl.YoutubeDL(ytdl_opts) as ytdl:
            ytdl.download([video_url])

        return True

    def getInfo(self, path: str, video_url: str):
        """Fetch metadata for YouTube video

        Args:
            Requires - video_url (str) - The link of the YouTube video
            Requires - path (str) - The parent directory to store the downloaded video
        Returns:
            JSON Object
        """
        ydl_opts = {
            'cookiefile': self.cookies,
            'logger': MyLogger(),
            'progress_hooks': [self.my_hook]
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            metadata = ydl.extract_info(video_url, download=False)
        #return metadata
        year = metadata.get('upload_date')[:4]
        title = metadata.get('title', '').replace(":", "-")

        info = {
            'year': year,
            'title': f'{title} ({year})'

        }
