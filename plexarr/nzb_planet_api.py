import os
from configparser import ConfigParser
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


class NzbPlanetAPI(object):
    def __init__(self):
        """Constructor requires API-URL and API-KEY

        From config:
            api_url (str): API url for sonarr or radarr.
            api_key (str): API key for sonarr or radarr.
        """
        config = ConfigParser()
        config.read(os.path.join(os.path.expanduser('~'), '.config', 'plexarr.ini'))

        self.api_url = config['nzb_planet'].get('api_url').strip('/') + '/'
        self.api_key = config['nzb_planet'].get('api_key')
        self.session = requests.Session()


    def get(self, path, data={}):
        """Wrapper on session.get()
        Args:
            path: The endpoint for API
            data: Parameters to pass in dict() format
        """

        data.update({"apikey": self.api_key, "o": "json"})
        url = urljoin(self.newznab, path.strip('/'))
        return self.session.get(url=url, params=data).json()

    def getUserInfo(self, username='', query=''):
        return self.get(path='/', data={'t': 'tvsearch', 'tvdbid': tvdb_id, 'q': query})
