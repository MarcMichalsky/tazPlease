import os
import requests
from requests.exceptions import HTTPError
from exceptions import TazDownloadFormatException
from exceptions import TazDownloadError
from bs4 import BeautifulSoup

dir_path = os.path.dirname(os.path.realpath(__file__)) + '/'


class TazDownloader:
    download_formats = ["pdf", "epub", "epubt", "html", "ascii", "mobi", "mobit"]
    BASE_URL = "https://dl.taz.de/"
    HEADERS = {"User-agent": 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/79.0.3945.130 Safari/537.36'}

    def __init__(self, taz_id: str, password: str, download_format: str = "pdf"):
        """
        :param taz_id:
        :param password:
        :param download_format:
        """
        self.taz_id = taz_id
        self.password = password
        if download_format in self.download_formats:
            self.download_url = self.BASE_URL + download_format
        else:
            raise TazDownloadFormatException

    def scrape_newspaper(self) -> list:
        """
        Scrapes the newspaper available for download from https://dl.taz.de/
        :return: a list of file names (str)
        """
        page = requests.get(self.download_url, headers=self.HEADERS)
        soup = BeautifulSoup(page.content, 'html.parser')
        return [n['value'] for n in soup.find("select").find_all("option")]

    def download_newspaper(self, taz: str, download_folder: str = dir_path + 'tmp/'):
        """
        Downloads a newspaper from dl.taz.de and stores it in /tmp
        """

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
