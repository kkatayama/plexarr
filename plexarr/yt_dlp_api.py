import json
import os
import shutil
from configparser import ConfigParser

import yt_dlp
import yt_dlp.utils
from rich import inspect, print
from rich.progress import Progress


class MyLogger(object):
    def info(self, msg):
        # print(msg)
        pass

    def debug(self, msg):
        if msg.startswith('[debug] '):
            pass
        else:
            self.info(msg)
        pass

    def warning(self, msg):
        # print(msg)
        pass

    def error(self, msg):
        # print(msg)
        pass

class FinishedPP(yt_dlp.postprocessor.PostProcessor):
    """
    THIS IS CALLED AFTER DOWNLOADING ALL PARTS!
    """
    def run(self, info):
        # self.to_screen("Finalizing Conversion....")
        print("Finalizing Conversion....")
        # print(inspect(info))
        return [], info

class YouTubeDLP(object):
    """Wrapper for YouTubeDLP via yt_dlp
    """
    def __init__(self):
        """Constructor

        From config:
            cookies (str): Path to Cookies File
        """
        config = ConfigParser()
        config.read(os.path.join(os.path.expanduser('~'), '.config', 'plexarr.ini'))

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

                self.download_status = True
                self.task = self.progress.add_task("[cyan]Downloading...", total=total)
                self.progress.start()

            step = int(d["downloaded_bytes"]) - int(self.downloaded_bytes)
            self.downloaded_bytes = int(d["downloaded_bytes"])
            self.progress.update(self.task, advance=step)
            # print(d['filename'], d['_percent_str'], d['_eta_str'])

    def getInfo(self, video_url='', **kwargs):
        self.video_url = video_url
        self.quiet = True
        self.verbose = False
        self.outtmpl = None
        self.writethumbnail = False
        self.writeinfojson = False
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
            'default_search': 'ytsearch10',
            'skip_download': True,
            'format': f'{video_format}+{audio_format}',
            'logger': MyLogger(),
            'progress_hooks': [self.d_hook]
        }

        with yt_dlp.YoutubeDL(ytdl_opts) as ytdl:
            ytdl.add_post_processor(FinishedPP())
            msize = media["file_size"]
            results = ytdl.extract_info(query, download=False)
            matches = [r for r in results["entries"] if ((r is not None) and (abs(msize-r["filesize_approx"]) < 1000000))]
            print(f'results: {len(results["entries"])}, matches: {len(matches)}')
            return matches

    def downloadVideo(self, title='', video_url='', path='', **kwargs):
        """downlod youtube video into folder

        args:
            requires - title (str)     - the video title
            requires - video_url (str) - the link of the youtube video
            requires - path (str)      - the output directory!

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
