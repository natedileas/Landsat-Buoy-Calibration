import narr
import merra


def download(source, metadata):
    """
    Download atmospheric data.
    """
    source = narr if source == 'narr' else merra
    source.download(metadata)


def process(source, metadata):
    """
    process atmospheric data, yield an atmosphere
    """
    source = narr if source == 'narr' else merra
    return source.calc_profile(metadata)
