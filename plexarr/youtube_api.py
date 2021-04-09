from rich.progress import Progress
from rich import print
from configparser import ConfigParser
import youtube_dl
import os


class MyLogger(object):
    def debug(self, msg):
        # print(msg)
        pass

    def warning(self, msg):
        # print(msg)
        pass

    def error(self, msg):
        print(msg)


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
        print(d)
        if d['status'] == 'finished':
            self.progress.stop()
            file_tuple = os.path.split(os.path.abspath(d['filename']))
            print("Done downloading {}".format(file_tuple[1]))
        if d['status'] == 'downloading':
            if not self.download_status:
                total = int(d["total_bytes"])
                self.download_status = True
                self.task = self.progress.add_task("[cyan]Downloading...", total=total)
                self.progress.start()
            step = int(d["downloaded_bytes"]) - int(self.downloaded_bytes)
            self.downloaded_bytes = int(d["downloaded_bytes"])
            self.progress.update(self.task, advance=step)
            # print(d['filename'], d['_percent_str'], d['_eta_str'])


    def downloadMovie(self, title='', video_url=''):
        """Downlod YouTube video into folder

        Args:
            Requires - folder (str) - The video title to store the downloaded video
            Requires - video_url (str) - The link of the YouTube video
        """
        self.title = title
        self.folder = os.path.join(self.path, title)
        self.f_name = os.path.join(self.path, title, f'{title}.mp4')
        if not os.path.exists(self.folder):
            print(f'creating directory: "{self.folder}"')
            os.mkdir(self.folder)

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

    def getInfo(self, path='', video_url=''):
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
