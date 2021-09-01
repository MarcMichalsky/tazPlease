import sys
import os
import datetime
import logging
import shutil
from envyaml import EnvYAML
from models import TazDownloader
import pandas as pd

dir_path = os.path.dirname(os.path.realpath(__file__)) + '/'

# Set up logging
logging.basicConfig(
    filename=dir_path + 'tazPlease.log',
    level=logging.ERROR,
    format='%(asctime)s - %(message)s'
)

# Load configuration
try:
    config = EnvYAML(dir_path + 'config.yaml', dir_path + '.env')
except Exception:
    logging.error('Could not load config.yaml', exc_info=True)
    sys.exit(1)

# Set log level
try:
    logging.getLogger().setLevel(config['logging']['log_level'].upper())
except ValueError as e:
    logging.error(f"Could not set log level. \n{e}", exc_info=True)

# Read download history from csv file
try:
    df = pd.read_csv(dir_path + 'download_history.csv', header=0)
except FileNotFoundError:
    # In case, there isn't yet a csv file, create data frame with headers
    df = pd.DataFrame(
        columns=[
            'file',
            'download_timestamp',
        ]
    )

# Instantiate downloader object
taz_dl = TazDownloader(config['taz']['taz_id'], config['taz']['taz_password'])

try:
    # Get newspapers available for download
    newspaper_available = taz_dl.scrape_newspaper()

    # Remove outdated newspaper from download_history.csv
    df.drop([f.index for f in df['file'] if f not in newspaper_available], inplace=True)

    # Find newspaper which are not already downloaded
    newspaper_to_download = [n for n in newspaper_available if n not in df.file.values]
except Exception as e:
    logging.error(f"Could get available newspaper from website\n{e}", exc_info=True)
    sys.exit(1)

# Download newspaper
newspaper_downloaded = []
for n in newspaper_to_download:
    try:
        if taz_dl.download_newspaper(n):
            newspaper_downloaded.append(n)
    except Exception as e:
        logging.error(f"Could not download {n}\n{e}", exc_info=True)

# Add downloaded newspaper to download_history.csv
try:
    for n in newspaper_downloaded:
        df_tmp = pd.DataFrame(
            {
                'file': [n],
                'download_timestamp': [datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S')],
            }
        )
        df = df.append(df_tmp, ignore_index=True)
    df.sort_values(by='download_timestamp', ascending=False, inplace=True)
    df.to_csv(dir_path + 'download_history.csv', index=False)
except Exception as e:
    logging.error(f"Could not update download_history.csv\n{e}", exc_info=True)

# Move downloaded file to download folder
if os.path.isdir(config['download_folder']):
    download_folder = \
        config['download_folder'] if config['download_folder'].endswith('/') else config['download_folder'] + "/"
    for n in newspaper_downloaded:
        try:
            shutil.move(dir_path + 'tmp/' + n, download_folder)
        except Exception as e:
            logging.error(f"Could not move file to download folder \"{download_folder}\"\n{e}", exc_info=True)
