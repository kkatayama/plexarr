import json
import os
# import shutil
from configparser import ConfigParser
from pathlib import Path

import yt_dlp
import yt_dlp.utils
from rich import print, inspect
from rich.progress import Progress


class MyLogger(object):
    """Handle Log Output"""

    def info(self, msg):
        """Info"""
        # print(msg)
        pass

    def debug(self, msg):
        """Debug"""
        if msg.startswith('[debug] '):
            pass
        else:
            self.info(msg)
        pass

    def warning(self, msg):
        """Warning"""
        # print(msg)
        pass

    def error(self, msg):
        """Error"""
        # print(msg)
        pass


class FinishedPP(yt_dlp.postprocessor.PostProcessor):
    """CALLED AFTER DOWNLOADING ALL PARTS!"""

    def run(self, info):
        """Only Function"""
        # self.to_screen("Finalizing Conversion....")
        print("Finalizing Conversion....")
        print(inspect(info))
        return [], info


class YouTubeDLP(object):
    """Wrapper for YouTubeDLP via yt_dlp"""

    def __init__(self):
        """Init Constructor

        From config:
            cookies (str): Path to Cookies File
        """
        config = ConfigParser()
        # config.read(os.path.join(os.path.expanduser('~'), '.config', 'plexarr.ini'))
        config.read(Path.home().joinpath(".config", "plexarr.ini"))

        self.path = config['youtube'].get('path')
        self.temp_dir = config['youtube'].get('temp_dir')
        self.cookies = config['youtube'].get('cookies')
        self.headers = None
        self.progress = Progress()
        self.task = None
        self.downloaded_bytes = 0
        self.download_status = False

    def d_hook(self, d):
        """
        SEE: https://stackoverflow.com/a/58667850/3370913

        THIS IS POLLED WHILE DOWNLOADING...
        """
        # print(d)
        if d['status'] == 'finished':
            self.download_status = False
            self.progress.stop()
            file_tuple = os.path.split(os.path.abspath(d['filename']))
            print(f'Done downloading "{file_tuple[1]}"')

        if d['status'] == 'downloading':
            if not self.download_status:
                if d.get('total_bytes'):
                    total = d["total_bytes"]
                elif d.get("total_bytes_estimate"):
                    total = d["total_bytes_estimate"]
                else:
                    total = 1
                file_tuple = os.path.split(os.path.abspath(d["filename"]))
                self.download_status = True
                self.task = self.progress.add_task(f'[cyan]Downloading[/]: [yellow]"{file_tuple[1]}"[/]', total=total)
                self.progress.start()

            step = int(d["downloaded_bytes"]) - int(self.downloaded_bytes)
            self.downloaded_bytes = int(d["downloaded_bytes"])
            self.progress.update(self.task, advance=step)
            # print(d['filename'], d['_percent_str'], d['_eta_str'])

    def getInfo(self, video_url='', **kwargs):
        """Info JSON"""
        self.video_url = video_url
        self.quiet = True
        self.verbose = False
        self.outtmpl = None
        self.writethumbnail = False
        self.writeinfojson = False
        self.extract_flat = False
        self.forcethumbnail = False
        self.__dict__.update(kwargs)

        if not self.video_url:
            print('[red]YOU NEED TO SET: video_url[/]')
            return

        ytdl_opts = {
            'quiet': self.quiet,
            'verbose': self.verbose,
            'overwrites': None,
            'writethumbnail': self.writethumbnail,
            'writeinfojson': self.writeinfojson,
            'extract_flat': self.extract_flat,
            'forcethumbnail': self.forcethumbnail,
            'noplaylist': True,
            'skip_download': True,
            'clean_infojson': False,
            'outtmpl': self.outtmpl,
            'ignoreerrors': False,
            'cookiefile': self.cookies,
            'format': "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            'logger': MyLogger(),
            'progress_hooks': [self.d_hook]
        }

        with yt_dlp.YoutubeDL(ytdl_opts) as ytdl:
            ytdl.add_post_processor(FinishedPP())
            data = ytdl.extract_info(self.video_url)
            info = ytdl.sanitize_info(data)
            self.data = data
            self.info = info
            return info

    def searchInfo(self, media, video, audio, query, **kwargs):
        """Search for Matching Video by MetaData"""
        self.__dict__.update(kwargs)
        vsize = video["stream_size"]
        asize = audio["stream_size"]
        width = video["width"]
        height = video["height"]
        vcodec = video["codec_id"].split("-")[0]
        acodec = audio["codec_id"].split("-")[0]

        fps = round(float(video["frame_rate"]))
        ext = media["file_extension"]
        asr = audio["sampling_rate"]

        video_format = f'bestvideo[height={height}][width={width}][ext={ext}][fps={fps}][vcodec*={vcodec}][filesize>={vsize}]'
        audio_format = f'bestaudio[acodec*={acodec}][asr={asr}][filesize>={asize}]'

        ytdl_opts = {
            'noplaylist': True,
            'ignoreerrors': True,
            'cookiefile': self.cookies,
            'default_search': 'ytsearch4',
            'skip_download': True,
            'format': f'{video_format}+{audio_format}',
            'logger': MyLogger(),
            'progress_hooks': [self.d_hook]
        }

        with yt_dlp.YoutubeDL(ytdl_opts) as ytdl:
            ytdl.add_post_processor(FinishedPP())
            msize = media["file_size"]
            results = ytdl.extract_info(query, download=False)
            self.search_results = results
            matches = [r for r in results["entries"] if ((r is not None) and (abs(msize-r["filesize_approx"]) < 1000000))]
            print(f'results: {len(results["entries"])}, matches: {len(matches)}')
            return matches

    def downloadVideo(self, title='', video_url='', path='', **kwargs):
        """Downlod youtube video into folder

        Args:
            title (str):     (Required) - the video title
            video_url (str): (Required) - the link of the youtube video
            path (str):      (Required) - the output directory!

        example:
            from plexarr import youtubedlp

            youtube = youtubedlp()
            youtube.downloadvideo(title=title, video_url=url, path=lib_path)

        """
        # -- setting up path configs
        self.title = title
        self.video_url = video_url
        self.path = path
        self.headers = False
        self.writethumbnail = False
        self.writeinfojson = False
        self.writesubtitles = True
        self.writeautomaticsub = False
        self.__dict__.update(kwargs)

        self.title = title
        self.path = path
        self.folder = os.path.join(self.path, self.title)
        self.f_name = os.path.join(self.path, self.title, f'{self.title}.mp4')

        # -- create fresh directory
        print(f'creating directory: "{self.folder}"')
        print(f'{{"video_url": {video_url}}}')
        os.makedirs(self.folder, exist_ok=True)

        ### Download Movie via yt-dlp ###
        ytdl_opts = {
            'writethumbnail': self.writethumbnail,
            'writeinfojson': self.writeinfojson,
            'writesubtitles': self.writesubtitles,
            'writeautomaticsub': self.writeautomaticsub,
            'subtitlesformat': 'vtt',
            'subtitleslangs': ['en'],
            'cookiefile': self.cookies,
            'format': "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            'outtmpl': self.f_name,
            'postprocessors': [{
                'key': 'FFmpegMetadata',
                'add_chapters': True,
                'add_metadata': True,
            },{
                'key': 'FFmpegSubtitlesConvertor',
                'format': 'vtt'
            }],
            'logger': MyLogger(),
            'progress_hooks': [self.d_hook]
        }

        if self.headers:
            yt_dlp.utils.std_headers.update(self.headers)

        with yt_dlp.YoutubeDL(ytdl_opts) as ytdl:
            # return ytdl.download_with_info_file(video_url)
            ytdl.add_post_processor(FinishedPP())
            data = ytdl.extract_info(video_url)
            info = json.dumps(ytdl.sanitize_info(data))
            self.data = data
            self.info = info
            return "Download Finished!"

    def downloadEpisode(self, url='', mp4_file='', **kwargs):
        """Downlod Episode into Season Path Folder

        Args:
            url (str):      (Required) - the video title
            mp4_file (str): (Required) - the link of the youtube video

        example:
            from plexarr import youtubedlp

            youtube = youtubedlp()
            youtube.downloadEpisode(video_url=url, mp4_file=mp4_file, format=format_quality)

        """
        # -- settings passed indirectly
        self.video_url = url
        self.f_name = mp4_file
        self.format = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        self.headers = False

        # -- settings passed directly
        self.writethumbnail = False
        self.writeinfojson = False
        self.writesubtitles = True
        self.writeautomaticsub = False
        self.subtitlesformat = 'srt'
        self.subtitleslangs = ['en']
        self.download_archive = False
        self.__dict__.update(kwargs)

        if '%' not in self.f_name:
            print(f'self.f_name = "{self.f_name}"')
            # -- create fresh directory
            self.folder = Path(self.f_name).parent
            print(f'creating directory: "{self.folder}"')
            print(f'{{"video_url": {self.video_url}}}')
            # os.makedirs(self.folder, exist_ok=True)
            self.folder.mkdir(exist_ok=True)
        else:
            print(f'"{url}"')

        # -- Download Movie via yt-dlp -- #
        ytdl_opts = {
            'writethumbnail': self.writethumbnail,
            'writeinfojson': self.writeinfojson,
            'writesubtitles': self.writesubtitles,
            'writeautomaticsub': self.writeautomaticsub,
            'subtitlesformat': self.subtitlesformat,
            'subtitleslangs': self.subtitleslangs,
            'download_archive': self.download_archive,
            'cookiefile': self.cookies,
            'format': self.format,
            'outtmpl': self.f_name,
            'postprocessors': [{
                'key': 'FFmpegMetadata',
                'add_chapters': True,
                'add_metadata': True,
            },{
                'key': 'FFmpegSubtitlesConvertor',
                'format': self.subtitlesformat
            }],
            'logger': MyLogger(),
            'progress_hooks': [self.d_hook]
        }

        if self.headers:
            yt_dlp.utils.std_headers.update(self.headers)

        with yt_dlp.YoutubeDL(ytdl_opts) as ytdl:
            # return ytdl.download_with_info_file(video_url)
            ytdl.add_post_processor(FinishedPP())
            data = ytdl.extract_info(self.video_url)
            info = json.dumps(ytdl.sanitize_info(data))
            self.data = data
            self.info = info
            # return "Download Finished!"
            retrun ytdl

    def dVideo(self, title='', video_url='', path='', **kwargs):
        """Downlod youtube video into folder

        Args:
            title (str):     (Required) - the video title
            video_url (str): (Required) - the link of the youtube video
            path (str):      (Required) - the output directory!

        example:
            from plexarr import youtubedlp

            youtube = youtubedlp()
            youtube.downloadvideo(title=title, video_url=url, path=lib_path)

        """
        # -- setting up path configs
        self.title = title
        self.video_url = video_url
        self.path = path
        self.headers = False
        self.writethumbnail = False
        self.writeinfojson = False
        self.writesubtitles = True
        self.writeautomaticsub = False
        self.__dict__.update(kwargs)

        self.title = title
        self.path = path
        self.folder = self.path
        self.f_name = os.path.join(self.path, f'{self.title}.mp4')

        # -- create fresh directory
        print(f'creating directory: "{self.folder}"')
        print(f'{{"video_url": {video_url}}}')
        os.makedirs(self.folder, exist_ok=True)

        ### Download Movie via yt-dlp ###
        ytdl_opts = {
            'writethumbnail': self.writethumbnail,
            'writeinfojson': self.writeinfojson,
            'writesubtitles': self.writesubtitles,
            'writeautomaticsub': self.writeautomaticsub,
            'subtitlesformat': 'vtt',
            'subtitleslangs': ['en'],
            'cookiefile': self.cookies,
            'format': "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            'outtmpl': self.f_name,
            'postprocessors': [{
                'key': 'FFmpegMetadata',
                'add_chapters': True,
                'add_metadata': True,
            },{
                'key': 'FFmpegSubtitlesConvertor',
                'format': 'vtt'
            }],
            'logger': MyLogger(),
            'progress_hooks': [self.d_hook]
        }

        if self.headers:
            yt_dlp.utils.std_headers.update(self.headers)

        with yt_dlp.YoutubeDL(ytdl_opts) as ytdl:
            # return ytdl.download_with_info_file(video_url)
            ytdl.add_post_processor(FinishedPP())
            data = ytdl.extract_info(video_url)
            info = json.dumps(ytdl.sanitize_info(data))
            self.data = data
            self.info = info
            return "Download Finished!"
