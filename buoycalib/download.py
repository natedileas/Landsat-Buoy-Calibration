import os
from urllib.request import urlopen
import urllib.error
import gzip
import shutil
import warnings

import requests

CHUNK = 1024 * 1024 * 8   # 1 MB


class RemoteFileException(Exception):
    pass


def url_download(url, out_dir, _filename=None, auth=None):
    """ download a file (ftp or http), optional auth in (user, pass) format """

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    filename = _filename if _filename else url.split('/')[-1]
    filepath = os.path.join(out_dir, filename)

    if os.path.isfile(filepath):
        return filepath

    if url[0:3] == 'ftp':
        download_ftp(url, filepath)
    else:
        download_http(url, filepath, auth)

    return filepath


def download_http(url, filepath, auth=None):

    with requests.Session() as session:
        req = session.request('get', url)

        if auth:
            resource = session.get(req.url, auth=auth)

            if resource.status_code != 200:
                raise RemoteFileException('url: {0} does not exist'.format(url))
        else:
            if not _remote_file_exists(url, auth):
                raise RemoteFileException('url: {0} does not exist'.format(url))

            resource = session.get(req.url)

        with open(filepath, 'wb') as f:
            f.write(resource.content)

    return filepath


def download_ftp(url, filepath):
    try:
        request = urlopen(url)
    except urllib.error.URLError as e:
        print(url)
        raise RemoteFileException('url: {0} does not exist'.format(url))

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
        try:
           shutil.copyfileobj(f_in, f_out)
        except OSError as e:
            warnings.warn(str(e) + filepath, RuntimeWarning)

    return filepath


def untar(filepath):
    pass


def _remote_file_exists(url, auth=None):

    if auth:
        resp = requests.get(url, auth=auth)
        status = resp.status_code
    else:
        status = requests.head(url).status_code

    if status != 200:
        return False

    return True