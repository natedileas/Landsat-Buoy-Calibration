import os
from urllib.request import urlopen
import gzip
import shutil

import requests

CHUNK = 1024 * 1024 * 8   # 1 MB


class RemoteFileException(Exception):
    pass


def url_download(url, out_dir):
    """ download a file (ftp or http) """
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    filename = url.split('/')[-1]
    filepath = os.path.join(out_dir, filename)

    if os.path.isfile(filepath):
        return filepath

    request = urlopen(url)

    with open(filepath, 'wb') as fileobj:
        while True:
            chunk = request.read(CHUNK)
            if not chunk:
                break
            fileobj.write(chunk)

    return filepath


def ungzip(filepath):
    """ un-gzip a fiile (equivalent of `gzip -d filepath`) """
    new_filepath = filepath.replace('.gz', '')
    with open(new_filepath, 'wb') as f_out, gzip.open(filepath, 'rb') as f_in:
        shutil.copyfileobj(f_in, f_out)

    return new_filepath


def remote_file_exists(url):
    status = requests.head(url).status_code

    if status != 200:
        raise RemoteFileException('File {0} doesn\'t exist.'.format(url))
