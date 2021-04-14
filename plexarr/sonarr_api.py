from .requests_api import RequestsAPI
from .utils import camel_case
from configparser import ConfigParser
from rich.console import Console
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

        self.api_url = config['sonarr'].get('api_url')
        self.api_key = config['sonarr'].get('api_key')
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
            path = '/Episode'
            data = {
                'seriesId': series_id
            }
            res = self.get(path=path, data=data)
            return res

        if title:
            series = self.getSeries()
            show = next(filter(lambda x: x['title'] == title, series), None)
            path = '/Episode'
            data = {
                'seriesId': show.get('id')
            }
            res = self.get(path=path, data=data)
            return res

    def getEpisodeFiles(self, title='', series_id=-1):
        """Returns all episode files for the given seriesId

        Args:
            Optional - title (str) - The title of the TV Show
            Optional - series_id (int) - The Sonarr series_id
        Returns:
            JSON Array
        """
        if title:
            series = self.getSeries()
            show = next(filter(lambda x: x['title'] == title, series), None)
            series_id = show.get('id')
        if series_id >= 0:
            data = {
                'seriesId': series_id
            }

        path = '/EpisodeFile'
        res = self.get(path=path, data=data)
        return res

    def getEpisodeFile(self, episode_file_id=-1, title='', s_num=-1, e_num=-1):
        c = Console()
        if ((s_num >= 0) and (e_num >= 0) and (title)):
            ep_all = self.getEpisodes(title=title)
            ep_info = next(filter(lambda x: x['seasonNumber'] == s_num and x['episodeNumber'] == e_num, ep_all), None)
            episode_id = ep_info["episodeFileId"]
            c.print(ep_all)
            c.print(ep_info)
            c.print(episode_id)

        path = f'/EpisodeFile/{episode_file_id}'
        res = self.get(path=path)
        return res

    def editEpisode(self, episode_data):
        """Edit an Episode
        Args:
            Required - episode_data (dict) - data containing Episode changes (do getEpisodes() first)
        Returns:
            JSON Response
        """
        path = '/Episode'
        data = episode_data
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

    def importDownloadedEpisode(self, episode_path, **kwargs):
        """Scan the provided episode_path for downloaded episode and import to Sonarr collection

        Args:
            Required - episode_path (str) - Full path to downloaded episode (folder name should be {release name}/{Season #})
            Optional - import_mode (str) - "Move", "Copy", or "Hardlink" (default: "Move")
        Returns:
            JSON Response
        """
        path = '/command'
        data = {
            'name': 'DownloadedEpisodesScan',
            'path': episode_path,
            'importMode': 'Move'
        }
        data.update({camel_case(key): kwargs.get(key) for key in kwargs})
        res = self.post(path=path, data=data)
        return res
