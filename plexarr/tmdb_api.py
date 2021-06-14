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

    def searchMovie(self, query='', year=None):
        """Search for movie in The Movie Database

        Args:
            Requires - query (str) - The Movie Title to search
            Optional - year (str) - The Release Year
        Returns:
            JSON Array
        """
        search = self.tmdb.Search()

        if year:
            return search.movie(query=query, year=year)
        return search.movie(query=query)

