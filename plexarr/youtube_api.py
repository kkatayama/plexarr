from configparser import ConfigParser
import youtube_dl
import os

class MyLogger(object):
    def debug(self, msg):
        #print(msg)
        pass

    def warning(self, msg):
        #print(msg)
        pass

    def error(self, msg):
        print(msg)


def my_hook(d):
    if d['status'] == 'finished':
        print('Done downloading, now converting ...')

def downloadMovie(path, video_url):
    ydl_opts = {
        'cookiefile': '/Users/katayama/cookies.txt',
        'logger': MyLogger(),
        'progress_hooks': [my_hook]
    }


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

        self.cookies = config['youtube'].get('cookies')


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
            'progress_hooks': [my_hook]
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
