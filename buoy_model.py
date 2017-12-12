
import buoycalib


def buoy_forward_model(buoy_id, date):

    buoy = buoycalib.buoy.all_datasets()[buoy_id]
    buoy.calc_info(date)
    print('{0}, {1}, {2:3.3f}, {3:3.3f}'.format(buoy.id, date.strftime('%Y/%m/%d:%H'), buoy.bulk_temp, buoy.skin_temp))


if __name__ == '__main__':
    import argparse
    import datetime

    parser = argparse.ArgumentParser(description='')

    parser.add_argument('buoy_id', help='NOAA Buoy ID. Example: 44009')
    parser.add_argument('date', help='Date in \"YYYY/MM/DD:HR\" format, can input multiple', nargs='+')

    args = parser.parse_args()

    dates = [datetime.datetime.strptime(d, '%Y/%m/%d:%H') for d in args.date]

    print('Buoy ID, Date {YYYY/MM/DD:HR}, Bulk Temp [K], Skin Temp [K]')
    for d in dates:
        buoy_forward_model(args.buoy_id, d)