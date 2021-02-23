import config
from .requests_api import RequestsAPI


class RadarrAPI(RequestsAPI):
    def __init__(self):
        """Constructor requires API-URL and API-KEY

        From config:
            api_url (str): API url for sonarr or radarr.
            api_key (str): API key for sonarr or radarr.
        """

        self.api_url = config.radarr.get('api_url')
        self.api_key = config.radarr.get('api_key')
        super().__init__(api_url=self.api_url, api_key=self.api_key)

    def getMovies(self):
        path = '/movie'
        data = {}
        res = self.get(path=path, data=data)
        return res
