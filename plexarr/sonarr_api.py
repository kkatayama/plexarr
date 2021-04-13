from .requests_api import RequestsAPI
from .utils import camel_case
from configparser import ConfigParser
import os


class SonarrAPI(RequestsAPI):
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

    def getSeries(self):
        """Get all series in the Sonarr collection

        Returns:
            JSON Array
        """
        path = '/series'
        res = self.get(path=path)
        return res

    def getShow(self, title='', series_id=-1):
        """Get a tv_show from the Sonarr collection by title or series_id

        Args:
            Optional - title (str) - The title of the TV Show
            Optional - series_id (int) - The Sonarr series_id
        Returns:
            JSON Object
        Requirements:
            one argument must be provided (title or series_id)
        """
        if series_id >= 0:
            path = f'/series/{series_id}'
            res = self.get(path=path)
            return res

        if title:
            series = self.getSeries()
            show = next(filter(lambda x: x['title'] == title, series), None)
            return show

        return {'ERROR': 'A title or series_id parameter is required'}

    def getEpisodes(self, title='', series_id=-1):
        """Returns all episodes for the given series

        Args:
            Optional - title (str) - The title of the TV Show
            Optional - series_id (int) - The Sonarr series_id
        Returns:
            JSON Array
        """

        if series_id >= 0:
            path = f'/Episode/{series_id}'
            res = self.get(path=path)
            return res

        if title:
            series = self.getSeries()
            show = next(filter(lambda, ['title'] == title, series), None)
            path = '/'
            return show


    def editMovie(self, movie_data):
        """Edit a Movie
        Args:
            Required - movie_data (dict) - data containing Movie changes (do getMovie() first)
        Returns:
            JSON Response
        """
        path = '/movie'
        data = movie_data
        res = self.put(path=path, data=data)
        return res

    def getIndexers(self):
        """Get a list of all Download Indexers

        Returns:
            JSON Array
        """
        path = '/indexer'
        res = self.get(path=path)
        return res

    def getIndexer(self, indexer_id):
        """Get a single Download Indexer by indexer_id

        Args:
            Required - indexer_id (int) - ID of the Download Indexer
        Returns:
            JSON Object
        """
        path = f'/indexer/{indexer_id}'
        res = self.get(path=path)
        return res

    def editIndexer(self, indexer_id, indexer_data):
        """Edit a Download Indexer by indexer_id

        Args:
            Required - indexer_id (int) - ID of the Download Indexer to edit
            Required - indexer_data (dict) - data containing the Download Indexer changes (do getIndexer() first)
        Returns:
            JSON Response
        """
        path = f'/indexer/{indexer_id}'
        data = indexer_data
        res = self.put(path=path, data=data)
        return res

    def importDownloadedMovie(self, movie_path, **kwargs):
        """Scan the provided movie_path for downloaded movie and import to Sonarr collection

        Args:
            Required - movie_path (str) - Full path to downloaded movie (folder name should be the release name)
            Optional - import_mode (str) - "Move", "Copy", or "Hardlink" (default: "Move")
        Returns:
            JSON Response
        """
        path = '/command'
        data = {
            'name': 'DownloadedEpisodesScan',
            'path': movie_path,
            'importMode': 'Move'
        }
        data.update({camel_case(key): kwargs.get(key) for key in kwargs})
        res = self.post(path=path, data=data)
        return res