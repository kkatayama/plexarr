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
