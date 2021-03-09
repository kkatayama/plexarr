from .requests_api import RequestsAPI
from .utils import camel_case
from configparser import ConfigParser
import os


class RadarrAPI(RequestsAPI):
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

    def getMovies(self):
        """Get all movies in the Radarr collection

        Returns:
            JSON Array"""
        path = '/movie'
        res = self.get(path=path)
        return res

    def getMovie(self, title='', movie_id=-1, tmdb_id=-1):
        """Get a movie from the Radarr collection by title or movie_id

        Args:
            Optional - title (str) - The title of the Movie
            Optional - movie_id (int) - The Radarr movie_id
        Returns:
            JSON Object
        Requirements:
            one argument must be provided (title or movie_id)
        """
        if tmdb_id >=0:
            path = '/movie'
            data = {
                'tmdbId': tmdb_id
            }
            res = self.get(path=path, data=data)
            return res

        if movie_id >= 0:
            path = f'/movie/{movie_id}'
            res = self.get(path=path)
            return res

        if title:
            movies = self.getMovies()
            movie = next(filter(lambda x: x['title'] == title, movies), None)
            return movie

        return {'ERROR': 'A title or movie_id parameter is required'}

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
        """Scan the provided movie_path for downloaded movie and import to Radarr collection

        Args:
            Required - movie_path (str) - Full path to downloaded movie (folder name should be the release name)
            Optional - import_mode (str) - "Move", "Copy", or "Hardlink" (default: "Move")
        Returns:
            JSON Response
        """
        path = '/command'
        data = {
            'name': 'DownloadedMoviesScan',
            'path': movie_path,
            'importMode': 'Move'
        }
        data.update({camel_case(key): kwargs.get(key) for key in kwargs})
        res = self.post(path=path, data=data)
        return res
