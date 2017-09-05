from . import narr
from . import merra


def process(source, metadata, buoy):
    """
    process atmospheric data, yield an atmosphere
    """
    source = narr if source == 'narr' else merra
    return source.calc_profile(metadata, buoy)
