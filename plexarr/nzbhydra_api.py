from .requests_api import RequestsAPI
from .utils import camel_case
from configparser import ConfigParser
from bs4 import BeautifulSoup
import os


class NZBHydraAPI(RequestsAPI):
    def __init__(self):
        """Constructor requires API-URL and API-KEY

        From config:
            api_url (str): API url for sonarr or radarr.
            api_key (str): API key for sonarr or radarr.
        """
        config = ConfigParser()
        config.read(os.path.join(os.path.expanduser('~'), '.config', 'plexarr.ini'))

        self.api_url = config['radarr'].get('api_url')
        self.api_key = config['radarr'].get('api_key')
        super().__init__(api_url=self.api_url, api_key=self.api_key)

