import argparse
import os

import filetype
import requests
from bs4 import BeautifulSoup
from envyaml import EnvYAML
from requests.exceptions import HTTPError

from exceptions import TazDownloadFormatException, TazConfigurationError, TazDownloadError

dir_path = os.path.dirname(os.path.realpath(__file__))


class TazConfiguration:
    """
    This class represents the configuration that is needed to run the program.
    On initialization it trys to load the configuration from either the config.yaml or from the arguments passed.
    """

    # List of tuples that each defines a single configuration that can be set either in the config.yaml by passing it
    # as an argument.
    # CONFIGURATIONS[0]: configuration name
    # CONFIGURATIONS[1]: is it required?
    CONFIGURATIONS = [
        ('id', True),
        ('password', True),
        ('download_format', False),
        ('download_folder', False),
        ('nextcloud_webdav_url', False),
        ('nextcloud_webdav_password', False),
        ('limit_requests', False),
        ('log_level', False),
    ]

    def __init__(self):
        self._config = {}

        # try to load configuration
        try:
            self._load_config()
        except TazDownloadFormatException:
            raise
        except Exception:
            raise

    def _load_config(self):
        # Try to load config.yaml
        try:
            conf_yaml = EnvYAML(os.path.join(dir_path, 'config.yaml'), os.path.join(dir_path, '.env'))
        except Exception as e:
            raise Exception(f"Something went wrong when reading config.yaml.\n{e}")

        # Get console arguments
        console_args = self._parse_arguments()

        # Set configurations by preferring console arguments over settings in config.yaml
        for conf, required in self.CONFIGURATIONS:
            if conf in console_args and getattr(console_args, conf) is not None:
                self._config[conf] = getattr(console_args, conf)
            elif conf_yaml.get(conf, None) is not None:
                self._config[conf] = conf_yaml[conf]
            else:
                if required:
                    raise TazConfigurationError(conf)

    def _parse_arguments(self):
        """
        Parse command line arguments.
        """
        argparser = argparse.ArgumentParser(
            description='Download taz e-paper',
        )
        argparser.add_argument(
            '-i',
            '--id',
            action='store',
            type=str,
            help='Your taz-ID',
        )
        argparser.add_argument(
            '-p',
            '--password',
            action='store',
            type=str,
            help='Your password',
        )
        argparser.add_argument(
            '-f',
            '--download-format',
            action='store',
            type=str,
            choices=['pdf', 'epub', 'epubt', 'html', 'ascii', 'mobi', 'mobit'],
            help='The e-paper format',
        )
        argparser.add_argument(
            '-d',
            '--download_folder',
            action='store',
            type=str,
            help='The path to a folder where the e-paper should be stored',
        )
        argparser.add_argument(
            '--nextcloud_webdav_url',
            action='store',
            type=str,
            help='The url of a Nextcloud webdav',
        )
        argparser.add_argument(
            '--nextcloud_webdav_password',
            action='store',
            type=str,
            help='The webdav password',
        )
        argparser.add_argument(
            '-l',
            '--limit-requests',
            action='store_true',
            default=None,
            help='Only query website for available newspaper if tomorrow\'s newspaper has not already been downloaded',
        )
        argparser.add_argument(
            '--log_level',
            action='store',
            choices=['notset', 'debug', 'info', 'warning', 'error', 'critical'],
            help='Set the log level',
        )
        return argparser.parse_args()

    def get_config(self) -> dict:
        return self._config


class TazDownloader:
    download_formats = ["pdf", "epub", "epubt", "html", "ascii", "mobi", "mobit"]
    BASE_URL = "https://dl.taz.de/"
    HEADERS = {"User-agent": 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/79.0.3945.130 Safari/537.36'}

    def __init__(self, taz_id: str, password: str, download_format: str = "pdf"):
        self.taz_id = taz_id
        self.password = password
        if download_format in self.download_formats:
            self.download_url = self.BASE_URL + download_format
        else:
            raise TazDownloadFormatException(download_format)

    def scrape_newspaper(self) -> list:
        """
        Scrapes the newspaper available for download from https://dl.taz.de/
        :return: a list of file names (str)
        """
        try:
            page = requests.get(self.download_url, headers=self.HEADERS)
            soup = BeautifulSoup(page.content, 'html.parser')
            return [n['value'] for n in soup.find("select").find_all("option")]
        except HTTPError as http_e:
            raise TazDownloadError(f"Could not scrape available newspaper editions:\n{http_e}")

    def download_newspaper(self, taz: str, download_folder: str = os.path.join(dir_path, 'tmp')):
        """
        Downloads a newspaper from dl.taz.de and stores it in tmp folder
        """

        # Check if folder exists
        try:
            if not os.path.isdir(download_folder):
                os.makedirs(download_folder)
        except Exception as e:
            raise TazDownloadError(f"Could not find or create \"{download_folder}\":\n{e}")

        # download taz
        try:
            with requests.get(
                    self.download_url,
                    stream=True,
                    headers=self.HEADERS,
                    params={
                        'name': self.taz_id,
                        'password': self.password,
                        'id': taz,
                        'Laden': '+Laden+',
                    }
            ) as r:
                # write response to file
                with open(os.path.join(download_folder, taz), "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                # Unfortunately, the taz website does not respond with a http error code if the credentials are wrong.
                # So we have to check if the response is a pdf file or the html page with an error message.
                try:
                    if filetype.guess(os.path.join(download_folder, taz)).mime != 'application/pdf':
                        raise TazDownloadError()
                except (AttributeError, TazDownloadError) as e:
                    # Try to get the error message from the html file to put it in the log
                    with open(os.path.join(download_folder, taz), 'r') as f:
                        soup = BeautifulSoup(f.read(), 'html.parser')
                        error_displayed_on_page = soup.find('p', class_='error').text
                    if error_displayed_on_page:
                        os.remove(os.path.join(download_folder, taz))
                        raise TazDownloadError(error_displayed_on_page)
                    else:
                        os.remove(os.path.join(download_folder, taz))
                        raise TazDownloadError(e)
            return True
        except HTTPError as http_e:
            raise TazDownloadError(http_e)
