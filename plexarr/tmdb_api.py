import os
import sys
sys.path.append(os.path.join(os.path.expanduser('~'), '.config'))

import config
from .utils import camel_case
from .requests_api import RequestsAPI


class TmdbAPI(RequestsAPI):
    def __init__(self):
        """Constructor requires API-URL and API-KEY

        From config:
            api_url (str): API url for sonarr or radarr.
            api_key (str): API key for sonarr or radarr.
        """
        self.api_url = config.tmdb.get('api_url')
        self.api_key = config.tmdb.get('api_v4')
        super().__init__(api_url=self.api_url, api_key=self.api_key)

    def searchMovies(self, query=''):
        """Search for movie in The Movie Database

        Args:
            Requires - query (str) - The Movie Title to search
        Returns:
            JSON Array"""
        path = '/search'
        data = {
            'language': 'en-US',
            'query': query
        }
        res = self.get(path=path, data=data)
        return res

