from osgeo import ogr
import shapely.geometry
import shapely.wkt

# credit to here: 
# https://earthdatascience.org/tutorials/convert-landsat-path-row-to-lat-lon/

# shapefile from here: https://landsat.usgs.gov/pathrow-shapefiles
SHAPEFILE = "data/wrs2/wrs2_descending.shp"

class ogrError(Exception): pass


def wrs2_to_latlon(wrs2_path, wrs2_row, shapefile=SHAPEFILE):
    """ Convert a WRS-2 Path and Row to Latitude and Longitude """
    dataSource = ogr.Open(shapefile)
    layer = dataSource.GetLayer()

    for feature in layer:
        if feature['PATH'] == wrs2_path and feature['ROW'] == wrs2_row:
            geom = feature.GetGeometryRef()
            return geom.Centroid().GetX(), geom.Centroid().GetY()

    raise ogrError('Path and Row Not Found')


def latlon_to_wrs2(lat, lon, shapefile=SHAPEFILE):
    """ Convert Latitude and Longitude to a WRS-2 Path and Row """
    dataSource = ogr.Open(shapefile)
    layer = dataSource.GetLayer()
    point = shapely.geometry.Point(lat, lon)

    for feature in layer:
        geom = feature.GetGeometryRef()
        shape = shapely.wkt.loads(geom.ExportToWkt())
        if point.within(shape):
            return feature['PATH'], feature['ROW']

    raise ogrError('Lat and Lon Not Found')


if __name__ == '__main__':
    print 'Initial: 13, 33'
    lat, lon = wrs2_to_latlon(13, 33)
    print 'Lat: ',lat,' Lon: ',lon
    print 'Final: ', latlon_to_wrs2(lat, lon)
