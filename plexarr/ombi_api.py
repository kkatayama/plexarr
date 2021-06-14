from configparser import ConfigParser
from urllib.parse import urljoin
from datetime import datetime as dt
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

    def request(self, path, data=None, v2=False):
        import requests

        if v2:
            url = urljoin(self.ombi._base_url.replace('/v1', '/v2'), path.strip('/'))
        else:
            url = urljoin(self.ombi._base_url, path.strip('/'))
        headers = {
            "UserName": self.ombi._username,
            "ApiKey": self.ombi._api_key
        }

        if not data:
            res = requests.get(url=url, headers=headers, timeout=10)
        else:
            res = requests.post(url=url, headers=headers, json=data, timeout=10)
        return res

    def getMovieRequests(self):
        """Get all movies that have been requested

        NOTE: Identical to ombi.getAllMovies()

        Returns:
            JSON Array
        """

        path = '/Request/movie'
        return self.request(path=path).json()

    def getMovies(self):
        """Get all movies that have been requested by not yet downloaded

        Returns:
            JSON Array
        """
        return [m for m in self.ombi.get_movie_requests() if not m.get('available')]

    def getAllMovies(self):
        """Get all movies that have been requested

        Returns:
            JSON Array
        """
        return self.ombi.get_movie_requests()

    def searchMovie(self, query='', year=None, tmdb_id=None):
        """Search for a Movie [query or tmdb_id required]

        Args:
            Optional - query (str) - Movie title to search for
            Optional - year (int) - Movie released year to apply as a filter
            Optional - tmdb_id (int) - The Movie Database ID
        Returns:
            JSON Array
        """
        if query and not year:
            return self.ombi.search_movie(query=query)
        if not tmdb_id:
            path = f'/Search/movie/{tmdb_id}'
            return self.request(path=path, v2=True).json()
        try:
            return [m for m in self.ombi.search_movie(query=query) if dt.fromisoformat(m.get('releaseDate')).year == int(year)]
        except:
            return self.ombi.search_movie(query=query)

    def searchMulti(self, query='', movie=False, tv=False, music=False, people=False):
        """Search using Multi

        Args:
            Required - query (str) - Movie Title to search for
            Optional - movie (boolean) - Include Movie results
            Optional - movie (boolean) - Include TV Show results
            Optional - movie (boolean) - Include Music results
            Optional - movie (boolean) - Include People results
        Return:
            JSON Array
        """
        path = f'/Search/multi/{query}'
        data = {
            'movies': movie,
            'tvShows': tv,
            'music': music,
            'people': people
        }
        return self.request(path=path, data=data, v2=True).json()

    def getMovieRootPaths(self):
        """Get Radarr paths

        Returns:
            JSON Array
        """
        path = '/Radarr/RootFolders'
        return self.request(path=path).json()

    def requestMovie(self, tmdb_id='', language='', quality_id='', path_id=''):
        """Request a Movie to be added to Radarr

        Args:
            Required - tmdb_id (str) - The Movie DB ID
            Optional - quality_id (str) - Index of Radarr Quality Profile
            Optional - folder_id (str) - Index of Radarr Root Path ("4" = "movies5", "5" = "movies_old")
        Returns:
            JSON Array
        """
        path = '/Request/Movie'
        data = {
            "languageCode": language,
            "qualityPathOverride": quality_id,
            "rootFolderOverride": path_id,
            "theMovieDbId": tmdb_id
        }
        return self.request(path=path, data=data).json()
