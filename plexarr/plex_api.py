from ast import literal_eval
from configparser import ConfigParser
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from plexapi import utils
from plexapi.server import PlexServer
from rich import print
from rich.traceback import install

# -- Initialize -- #
install(show_locals=False)


class PlexPy(PlexServer):
    """Wrapper for python-plexapi
    """
    def __init__(self, server=1):
        """Constructor, requires API-URL and API-KEY"""
        config = ConfigParser()
        config.read(Path.home().joinpath(".config", "plexarr.ini"))
        self.ALERT_TYPES = literal_eval(config['plex'].get('ALERT_TYPES'))
        self.utils = utils
        self.server = 'plex' if int(float(server)) == 1 else f'plex{server}'
        self.api_url = config[self.server].get('api_url').strip('/') + '/'
        self.api_key = config[self.server].get('api_key')
        super().__init__(baseurl=self.api_url, token=self.api_key)


class PlexAPI(object):
    """Wrapper for Plex Web API
    """

    def __init__(self):
        """Constructor requires config file: plexarr.ini
        """
        config = ConfigParser()
        config.read(Path.home().joinpath(".config", "plexarr.ini"))

        self.api_url = config['plex'].get('api_url').strip('/') + '/'
        self.api_key = config['plex'].get('api_key')
        self.session = requests.Session()
        self.token = {
            'X-Plex-Token': f'{self.api_key}'
        }

    def get(self, path, data={}):
        """Wrapper on session.get()
        Args:
            path: The endpoint for API
            data: Parameters to pass in dict() format
        Returns:
            Response Object
        """

        data.update(self.token)
        url = urljoin(self.api_url, path.strip('/'))
        return self.session.get(url=url, params=data)

    def getMetaData(self, key: str, full=False):
        """Constructor requires rating_key
        Args:
            Required - key (str) - Plex rating-key associated with content (ex: key = '/library/metadata/91993')
        Returns:
            JSON Response
        """

        path = '/' + key.strip('/')
        res = self.get(path=path)
        soup = BeautifulSoup(res.content, 'xml')
        if full:
            return soup.select_one('MediaContainer')

        metadata = {
            'MediaContainer': soup.select_one('MediaContainer').attrs,
            'Video': soup.select_one('Video').attrs,
            'Media': soup.select_one('Media').attrs,
            'Streams': soup.select('Stream')
        }
        return metadata

    def getServerCapabilities(self):
        path = '/'
        res = self.get(path=path)
        return BeautifulSoup(res.content, 'xml')

    def getLibraries(self):
        path = '/library/sections'
        res = self.get(path=path)
        return BeautifulSoup(res.content, 'xml')

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

