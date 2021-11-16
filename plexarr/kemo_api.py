from configparser import ConfigParser
from pathlib import Path
from urllib.parse import urljoin

import requests


class KemoAPI(object):
    """REST API Wrapper for GitHub"""

    def __init__(self):
        """Configs"""
        config = ConfigParser()
        config.read(Path(Path.home(), '.config/plexarr.ini'))

        self.API_URL = config["kemo"].get('api_url')
        self.USERNAME = config["kemo"].get('username')
        self.PASSWORD = config["kemo"].get('password')
        self.PARAMS = {
            "username": self.USERNAME,
            "password": self.PASSWORD
        }
        self.CATEGORY = {}
        self.STREAMS = {}

    def getCategory(self, query=''):
        """Get Category using query filter"""
        payload = self.PARAMS
        payload.update({'action': 'get_live_categories'})
        r = requests.get(url=self.API_URL, params=payload)
        return next((cat for cat in r.json() if query.lower() in cat.get('category_name').lower()), {})

    def setCategory(self, query=''):
        """Set Category using 'query' filter"""
        payload = self.PARAMS
        payload.update({'action': 'get_live_categories'})
        r = requests.get(url=self.API_URL, params=payload)
        self.CATEGORY = next((cat for cat in r.json() if query.lower() in cat.get('category_name').lower()), {})

    def getStreams(self, terms=''):
        """Get Streams by Category_ID and filtered by 'terms'"""
        payload = self.PARAMS
        payload.update({'action': 'get_live_live_streams'})
        payload.update({'category_id': self.CATEGORY.get("category_id")})
        r = requests.get(url=self.API_URL, params=payload)
        return [stream for stream in r.json() if terms.lower() in stream.get('name').lower()]

    def getStreamsNFL(self):
        """Set NFL Streams"""
        self.setCategory(query="NFL")
        self.STREAMS = self.getStreams(terms="USA NFL Sunday 7")
        return self.STREAMS

    def getStreamsNBA(self):
        """Set NFL Streams"""
        self.setCategory(query="NBA")
        streams_1 = self.getStreams(terms="USA NBA 0")
        streams_2 = self.getStreams(terms="USA NBA 1")
        self.STREAMS = streams_1 + streams_2
        return self.STREAMS
