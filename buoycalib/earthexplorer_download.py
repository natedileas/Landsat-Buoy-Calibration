import urllib.request
import urllib.parse
import urllib.error
import re

def connect_earthexplorer_no_proxy(username, password):
    # mkmitchel (https://github.com/mkmitchell) solved the token issue
    cookies = urllib.request.HTTPCookieProcessor()
    opener = urllib.request.build_opener(cookies)
    urllib.request.install_opener(opener)
    
    data = urllib.request.urlopen("https://ers.cr.usgs.gov").read()
    m = re.search(r'<input .*?name="csrf_token".*?value="(.*?)"', data)
    if m:
        token = m.group(1)
    else:
        print("Error : CSRF_Token not found")
        sys.exit(-3)
        
    params = urllib.parse.urlencode(dict(username=username, password=password, csrf_token=token))
    request = urllib.request.Request("https://ers.cr.usgs.gov/login", params, headers={})
    f = urllib.request.urlopen(request)

    data = f.read()
    f.close()
    if data.find('You must sign in as a registered user to download data or place orders for USGS EROS products')>0:
        # auth failed, TODO raise warning
        return False

    return True


def download_landsat_earthexplorer(url, out_file):
    """ 
    """ 
    try:
        req = urllib.request.urlopen(url)
    
        #if downloaded file is html
        if (req.info().gettype()=='text/html'):
            raise ValueError("error : file is in html and not an expected binary file, url: {0}".format(url))

        #if file too small           
        total_size = int(req.info().getheader('Content-Length').strip())
        if (total_size<50000):
           raise ValueError("Error: The file is too small to be a Landsat Image, url: {0}".format(url))

        #download
        CHUNK = 1024 * 1024 *8

        with open(out_file, 'wb') as fp:
            while True:
                chunk = req.read(CHUNK)
                if not chunk: break
                fp.write(chunk)

    except urllib.error.HTTPError as e:
        if e.code == 500:
            raise ValueError("File doesn't exist url: {0}".format(url))
        else:
            raise ValueError("HTTP Error:" + e.code + url)
    
    except urllib.error.URLError as e:
        raise ValueError("URL Error: {1} url: {0}".format(url, e.reason))

    return out_file


#############################"Get metadata files
def getmetadatafiles(destdir,option):
    print 'Verifying catalog metadata files...'
    home = 'https://landsat.usgs.gov/landsat/metadata_service/bulk_metadata_files/'
    links=['LANDSAT_8.csv','LANDSAT_ETM.csv','LANDSAT_ETM_SLC_OFF.csv','LANDSAT_TM-1980-1989.csv','LANDSAT_TM-1990-1999.csv','LANDSAT_TM-2000-2009.csv','LANDSAT_TM-2010-2012.csv']
    for l in links:
        destfile = os.path.join(destdir,l)
        url = home+l
        if option=='noupdate':
            if not os.path.exists(destfile):
                print 'Downloading %s for the first time...'%(l)
                urllib.urlretrieve (url, destfile)
        elif option=='update':	
            urllib.urlretrieve (url, destfile)

if __name__ == '__main__':
    print(connect_earthexplorer_no_proxy('nid4986', 'Carlson89'))
    out = 'test.tar.gz'
    url = 'https://earthexplorer.usgs.gov/download/12864/LC80170302017328LGN00/STANDARD/EE'

    print(download_landsat_earthexplorer(url, out))