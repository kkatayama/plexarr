from configparser import ConfigParser
import tmdbsimple
import os


class TmdbAPI():
    """Wrapper for TMDB API via tmdbsimple

    """
    def __init__(self):
        """Constructor requires API-KEY

        From config:
            api_key (str): API key for TMDB.
        """
        config = ConfigParser()
        config.read(os.path.join(os.path.expanduser('~'), '.config', 'plexarr.ini'))

        self.tmdb = tmdbsimple
        self.tmdb.API_KEY = config['tmdb'].get('api_key')
        self.tmdb.API_URL = config['tmdb'].get('api_url')

    def searchMovie(self, query=''):
        """Search for movie in The Movie Database

        Args:
            Requires - query (str) - The Movie Title to search
        Returns:
            JSON Array
        """
        search = self.tmdb.Search()

        return search.movie(query=query)

