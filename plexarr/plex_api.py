from configparser import ConfigParser
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import requests
import os


class PlexAPI(object):
    """Wrapper for Plex Web API
    """
    def __init__(self):
        """Constructor requires config file: plexarr.ini
        """
        config = ConfigParser()
        config.read(os.path.join(os.path.expanduser('~'), '.config', 'plexarr.ini'))

        self.api_url = config['plex'].get('api_url').strip('/') + '/'
        self.api_key = config['plex'].get('api_key')
        self.session = requests.Session()
        self.token = {
            'X-Plex-Token': 'joLt2gmUQrN4fd5Uywsg'
        }


    def get(self, path, data={}):
        """Wrapper on session.get()
        Args:
            path: The endpoint for API
            data: Parameters to pass in dict() format
        """

        data.update(self.token)
        url = urljoin(self.api_url, path.strip('/'))
        return self.session.get(url=url, params=data)


    def getServerCapabilities(self):
        path = '/'
        res = self.get(path=path)
        return BeautifulSoup(res.content, 'html5lib')


    def getLibraries(self):
        path = '/library/sections'
        res = self.get(path=path)
        return BeautifulSoup(res.content, 'html5lib')


    def partialScan(self, library='', folder=''):
        s = self.getLibraries()
        for d in s.select('directory'):
            if d['title'] == library:
                print('key="{}" type="{}" title="{}"'.format(d['key'], d['type'], d['title']))
                break
        path = 'http://192.168.1.214:32400/library/sections/{}/refresh'.format(d['key'])
        data = {
            'path': folder
        }
        res = self.get(path=path, data=data)
        return res.reason

    def refreshGuide(self):
        headers = {
            'Connection': 'keep-alive',
            'Content-Length': '0',
            'sec-ch-ua': '"Chromium";v="90", "Opera";v="76", ";Not A Brand";v="99"',
            'Accept': 'text/plain, */*; q=0.01',
            'Accept-Language': 'en',
            'sec-ch-ua-mobile': '?0',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.51 Safari/537.36 OPR/76.0.4017.40 (Edition beta)',
            'Origin': 'http://192.168.1.214:32400',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': 'http://192.168.1.214:32400/',
        }

        params = (
            ('X-Plex-Product', 'Plex Web'),
            ('X-Plex-Version', '4.54.5'),
            ('X-Plex-Client-Identifier', 'amu0kss4i5a7hrz08zih4r6b'),
            ('X-Plex-Platform', 'Opera'),
            ('X-Plex-Platform-Version', '76.0'),
            ('X-Plex-Sync-Version', '2'),
            ('X-Plex-Features', 'external-media,indirect-media'),
            ('X-Plex-Model', 'bundled'),
            ('X-Plex-Device', 'OSX'),
            ('X-Plex-Device-Name', 'Opera'),
            ('X-Plex-Device-Screen-Resolution', '1577x981,1920x1080'),
            ('X-Plex-Token', 'hEYGzJAdKuaBJMYieCQ_'),
            ('X-Plex-Language', 'en'),
        )

        res = requests.post('https://192-168-1-214.b4b012fc348842c9b399bb4d103fcd5e.plex.direct:32400/livetv/dvrs/40/reloadGuide', headers=headers, params=params)
        return res.reason
    
