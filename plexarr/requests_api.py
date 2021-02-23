from urllib.parse import urljoin
import requests


class RequestsAPI:
    """Wrapper for requests()
    """
    def __init__(self, api_url: str, api_key: str):
        """Constructor requires API-URL and API-KEY
        Args:
            api_url (str): API url for sonarr or radarr.
            api_key (str): API key for sonarr or radarr.
        """

        self.api_url = api_url.strip('/') + '/'
        self.api_key = api_key
        self.session = requests.Session()
        self.auth = None
        self.headers = {
            'X-Api-Key': api_key,
            'Content-Type': 'application/json'
        }

    def get(self, path, data):
        """Wrapper on session.get()
        Args:
            path: The endpoint for API
            data: Parameters to pass in dict() format
        """
        url = urljoin(self.api_url, path.strip('/'))
        res = self.session.get(url=url, headers=self.headers, params=data)
        return res.json()

    def post(self, path, data):
        """Wrapper on session.get()
        Args:
            path: The endpoint for API
            data: Parameters to pass in dict() format
        """
        url = urljoin(self.api_url, path.strip('/'))
        res = self.session.post(url=url, headers=self.headers, json=data)
        return res.json()

    def put(self, path, data):
        """Wrapper on session.get()
        Args:
            path: The endpoint for API
            data: Parameters to pass in dict() format
        """
        url = urljoin(self.api_url, path.strip('/'))
        res = self.session.put(url=url, headers=self.headers, json=data)
        return res.json()

    def delete(self, path, data):
        """Wrapper on session.get()
        Args:
            path: The endpoint for API
            data: Parameters to pass in dict() format
        """
        url = urljoin(self.api_url, path.strip('/'))
        res = self.session.delete(url=url, headers=self.headers)
        return res.json()
