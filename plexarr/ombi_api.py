from configparser import ConfigParser
import pyombi
import os

class OmbiAPI():
    """Wrapper for TMDB API via tmdbsimple

    """
    def __init__(self):
        """Constructor requires Ombi info

        From config:
            api_key (str): API key.
        """
        config = ConfigParser()
        config.read(os.path.join(os.path.expanduser('~'), '.config', 'plexarr.ini'))

        self.ombi = pyombi.Ombi(
            ssl=config['ombi'].get('ssl'),
            host=config['ombi'].get('host'),
            port=config['ombi'].get('port'),
            urlbase=config['ombi'].get('urlbase'),
            username=config['ombi'].get('username'),
            password=config['ombi'].get('password'),
            api_key=config['ombi'].get('api_key')
        )
        self.ombi.authenticate()

    def getMovies(self):
        """Get all movies that have not been downloaded

        Returns:
            JSON Array
        """
        return [m for m in self.ombi.get_movie_requests() if not m.get('available')]

