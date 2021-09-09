import os
import requests
from requests.exceptions import HTTPError
from exceptions import TazDownloadFormatException
from exceptions import TazDownloadError
from bs4 import BeautifulSoup
from envyaml import EnvYAML
import argparse

dir_path = os.path.dirname(os.path.realpath(__file__)) + '/'


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
        ('download_folder', True),
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
            conf_yaml = EnvYAML(dir_path + 'config.yaml', dir_path + '.env')
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
            description='Download taz e-paper'
        )
        argparser.add_argument(
            '-i',
            '--id',
            action='store',
            type=str,
        )
        argparser.add_argument(
            '-p',
            '--password',
            action='store',
            type=str,
        )
        argparser.add_argument(
            '-f',
            '--download-format',
            action='store',
            type=str,
            choices=['pdf', 'epub', 'epubt', 'html', 'ascii', 'mobi', 'mobit'],
        )
        argparser.add_argument(
            '-d',
            '--download_folder',
            action='store',
            type=str,
        )
        argparser.add_argument(
            '-l',
            '--limit-requests',
            action='store_true',
            default=None
        )
        argparser.add_argument(
            '--log_level',
            action='store',
            choices=['notset', 'debug', 'info', 'warning', 'error', 'critical'],
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

    def download_newspaper(self, taz: str, download_folder: str = dir_path + 'tmp/'):
        """
        Downloads a newspaper from dl.taz.de and stores it in tmp/
        """

        # Check if folder exists
        try:
            if not os.path.isdir(dir_path):
                os.mkdirs(dir_path)
        except Exception as e:
            raise TazDownloadError(f"Could find or create \"{dir_path}\":\n{e}")

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
                with open(download_folder + taz, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            return True
        except HTTPError as http_e:
            raise TazDownloadError(f"Could not download taz:\n{http_e}")
        except Exception as e:
            raise TazDownloadError(f"Something went wrong:\n{e}")
