from osgeo import ogr
import shapely.geometry
import shapely.wkt

from . import settings

# credit to here: 
# https://earthdatascience.org/tutorials/convert-landsat-path-row-to-lat-lon/
# shapefile from here: https://landsat.usgs.gov/pathrow-shapefiles

class ogrError(Exception): pass


def wrs2_to_latlon(wrs2_path, wrs2_row, shapefile=settings.WRS2):
    """ Convert a WRS-2 Path and Row to Latitude and Longitude """
    dataSource = ogr.Open(shapefile)
    layer = dataSource.GetLayer()

    for feature in layer:
        if feature['PATH'] == wrs2_path and feature['ROW'] == wrs2_row:
            geom = feature.GetGeometryRef()
            return geom.Centroid().GetY(), geom.Centroid().GetX()

    raise ogrError('Path and Row Not Found')


def wrs2_to_corners(wrs2_path, wrs2_row, shapefile=settings.WRS2):
    """ Convert a WRS-2 Path and Row to Scene Corner Latitude and Longitude """
    dataSource = ogr.Open(shapefile)
    layer = dataSource.GetLayer()

    for feature in layer:
        if feature['PATH'] == wrs2_path and feature['ROW'] == wrs2_row:
            geom = feature.GetGeometryRef()
            return geom.GetEnvelope()[::-1]

    raise ogrError('Path and Row Not Found')


def latlon_to_wrs2(lat, lon, shapefile=settings.WRS2):
    """ Convert Latitude and Longitude to a WRS-2 Path and Row """
    dataSource = ogr.Open(shapefile)
    layer = dataSource.GetLayer()
    point = shapely.geometry.Point(lon, lat)

    for feature in layer:
        geom = feature.GetGeometryRef()
        shape = shapely.wkt.loads(geom.ExportToWkt())
        if point.within(shape):
            return feature['PATH'], feature['ROW']

    raise ogrError('Lat and Lon Not Found')


if __name__ == '__main__':
    print ('Lat, Lon: ', wrs2_to_latlon(13, 33))
    print ('WRS2: ', latlon_to_wrs2(-73.8077, 38.9073))
    print ('Corners: ', wrs2_to_corners(13, 33))
