import os
from urllib2 import urlopen

CHUNK = 1024 * 1024 * 8   # 1 MB


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
