from configparser import ConfigParser
from pathlib import Path
from urllib.parse import urljoin

import requests


class GitHubAPI(object):
    """REST API Wrapper for GitHub"""

    def __init__(self):
        """Configs"""
        config = ConfigParser()
        config.read(Path(Path.home(), '.config/plexarr.ini'))

        self.API_URL = config["github"].get('api_url')
        self.API_KEY = config["github"].get('api_key')
        self.HEADERS = {
            "User-Agent": "kkatayama",
            "Authorization": f'token {self.API_KEY}'
        }
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def get(self, path, data={}):
        """Session GET Wrapper"""
        url = urljoin(self.API_URL, path.strip('/'))
        s = self.session.get(url=url, params=data)
        return s.json()

    def getReleases(self, owner='', repo=''):
        """Get all releases"""
        path = f'/repos/{owner}/{repo}/releases'
        return self.get(path=path)

    def getTags(self, owner='', repo=''):
        """Get all tags"""
        path = f'/repos/{owner}/{repo}/tags'
        return self.get(path=path)
