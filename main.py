import logging
import os
import shutil
import sys
from datetime import datetime, timedelta
from urllib.parse import urlparse

import pandas as pd
import pytz
import validators
from webdav4.client import Client

from exceptions import TazConfigurationError, TazDownloadError, TazDownloadFormatException
from models import TazDownloader, TazConfiguration

# Get directory
dir_path = os.path.dirname(os.path.realpath(__file__))


def main(config: dict):
    # Get german date for tomorrow
    tomorrow = (datetime.now(pytz.timezone('Europe/Berlin')) + timedelta(1)).strftime('%Y_%m_%d')

    # Define tmp folder
    tmp_folder = os.path.join(dir_path, 'tmp')

    # Set log level
    try:
        logging.getLogger().setLevel(config['log_level'].upper())
    except ValueError as e:
        logging.error(f"Could not set log level.\n    {e}")

    # Read download history from csv file
    try:
        df = pd.read_csv(os.path.join(dir_path, 'download_history.csv'), header=0)
    except FileNotFoundError:
        # In case, there isn't yet a csv file, create data frame with headers
        df = pd.DataFrame(
            columns=[
                'file',
                'download_timestamp',
            ]
        )

    # If the 'limit_requests' argument is specified, check whether tomorrow's newspaper has already been downloaded
    if config['limit_requests']:
        try:
            if any(df.file.str.contains(pat=tomorrow)):
                logging.info('Tomorrow\'s newspaper was already downloaded. Execution canceled.')
                sys.exit(0)
        except Exception as e:
            logging.error(f"Could not check whether tomorrow's newspaper has already been downloaded.\n    {e}")

    # Instantiate downloader object
    try:
        taz_dl = TazDownloader(config['id'], config['password'], config['download_format'])
    except TazDownloadFormatException as e:
        logging.error(e)
        sys.exit(1)

    try:
        # Get newspaper available for download
        newspaper_available = taz_dl.scrape_newspaper()

        # Remove outdated newspaper from download_history.csv
        df.drop([index for index, row in df.iterrows() if row.file not in newspaper_available], inplace=True)

        # Find newspaper which are not already downloaded
        newspaper_to_download = [n for n in newspaper_available if n not in df.file.values]
    except TazDownloadError as e:
        logging.error(e)
        sys.exit(1)

    # Download newspaper
    newspaper_downloaded = []
    for n in newspaper_to_download:
        try:
            if taz_dl.download_newspaper(n, tmp_folder):
                newspaper_downloaded.append(n)
        except Exception as e:
            logging.error(f"Could not download {n}\n    {e}")

    # Add downloaded newspaper to download_history.csv
    try:
        for n in newspaper_downloaded:
            df_tmp = pd.DataFrame(
                {
                    'file': [n],
                    'download_timestamp': [datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')],
                }
            )
            df = df.append(df_tmp, ignore_index=True)
        df.sort_values(by='file', ascending=False, inplace=True)
        df.to_csv(os.path.join(dir_path, 'download_history.csv'), index=False)
    except Exception as e:
        logging.error(f"Could not update download_history.csv\n    {e}")

    newspaper_downloaded_string = "\n    ".join(newspaper_downloaded)

    if config['nextcloud_webdav_url']:
        if validators.url(config['nextcloud_webdav_url']):
            url = urlparse(config['nextcloud_webdav_url'])
            webdav_user = url.path.split("/")[-1]
            webdav_password = config['nextcloud_webdav_password']
            client = Client(f"{url.scheme}://{url.hostname}/public.php/webdav/",
                            auth=(webdav_user, webdav_password))

            for n in newspaper_downloaded:
                try:
                    client.upload_file(os.path.join(tmp_folder, n), n)
                    os.remove(os.path.join(tmp_folder, n))
                except Exception as e:
                    logging.error(f"Could not upload {n} to {url}\n    {e}")
            if newspaper_downloaded:
                logging.info(f"Uploaded\n    {newspaper_downloaded_string}\n    to {config['nextcloud_webdav_url']}")


        else:
            logging.error(f"Invalid url for Nextcloud webdav.")
            sys.exit(1)

    else:
        # If neither a webdav url nor a download folder was provided, exit the program here
        if not config['download_folder']:
            logging.error(f"Please provide a download folder or a Nextcloud webdav url.\n    {newspaper_downloaded_string}"
                          f"\n    downloaded to {tmp_folder}")
            sys.exit(1)

        # Move downloaded file to download folder
        if os.path.isdir(config['download_folder']):
            download_folder = \
                config['download_folder'] \
                    if config['download_folder'].endswith(os.path.sep) \
                    else config['download_folder'] + os.path.sep
            for n in newspaper_downloaded:
                try:
                    shutil.move(os.path.join(tmp_folder, n), download_folder)
                except Exception as e:
                    logging.error(f"Could not move {n} to download folder \"{download_folder}\"\n    {e}")
            if newspaper_downloaded:
                logging.info(f"Downloaded\n    {newspaper_downloaded_string}\n    to {config['download_folder']}")
        else:
            logging.error(f"{config['download_folder']} does not exists.\n    {newspaper_downloaded_string}"
                          f"\n    downloaded to {tmp_folder}")


if __name__ == '__main__':

    # Set up logging
    logging.basicConfig(
        filename=os.path.join(dir_path, 'tazPlease.log'),
        level=logging.ERROR,
        format='%(asctime)s - %(message)s'
    )

    # Load configuration
    try:
        configuration = TazConfiguration().get_config()
    except TazConfigurationError as tce:
        print(tce)
        sys.exit(1)
    except Exception as exception:
        print(exception)
        sys.exit(1)

    # Execute main function
    if configuration:
        main(configuration)
