from buoycalib import buoy

import matplotlib.pyplot as plt
import datetime
import numpy

buoy_id = '45012'
overpass_date = datetime.datetime(2010, 5, 2, 12)  # may 5th, 2010, noon

buoy_file = buoy.download(buoy_id, overpass_date)
data, headers, dates, units = buoy.load(buoy_file)
b = buoy.all_datasets()[buoy_id]
buoy_depth = b.thermometer_depth

#print(data)
print('Headers: ', headers)
print('Units: ', units)
print('Last Date in File: ', max(dates), 'First Date in File: ', min(dates), 'Resolution: ', dates[1] - dates[0])


# in order to perform a slice on the data
# you need a date/time slice and a header

# so for example, a 24 hr slice centered on the overpass date in water temperature
dt_slice = [i for i, d in enumerate(dates) if abs(d - overpass_date) < datetime.timedelta(hours=24)]
w_temp = data[dt_slice, headers.index('WTMP')]
wind_spd = data[dt_slice, headers.index('WSPD')]
#closest_dt = min([abs(overpass_date - d) for d in dates])
#closest_wtmp = data[dates.index(closest_dt), headers.index('WSPD')]


def calc_skin_temp(data, dates, headers, overpass_date, buoy_depth):
	dt = [(i, d) for i, d in enumerate(dates) if abs(d - overpass_date) < datetime.timedelta(hours=12)]
	dt_slice, dt_times = zip(*dt)
	w_temp = data[dt_slice, headers.index('WTMP')]
	wind_spd = data[dt_slice, headers.index('WSPD')]
	closest_dt = min([(i, abs(overpass_date - d)) for i, d in enumerate(dates)], key=lambda i: i[1])
	T_zt = data[closest_dt[0], headers.index('WSPD')]


	# 24 hour average wind Speed at 10 meters (measured at 5 meters) 
	u_m = wind_speed_height_correction(numpy.nanmean(wind_spd), 5, 10)
	
	avg_wtmp = numpy.nanmean(w_temp)

	a = 0.05 - (0.6 / u_m) + (0.03 * numpy.log(u_m))   # thermal gradient
	z = buoy_depth   # depth in meters

	avg_skin_temp = avg_wtmp - (a * z) - 0.17

	# part 2
	b = 0.35 + (0.018 * numpy.exp(0.4 * u_m))
	c = 1.32 - (0.64 * numpy.log(u_m))


	f_cz = (w_temp - avg_skin_temp) / numpy.exp(b*z)
	cz = datetime.timedelta(hours=c*z)
	f = numpy.interp(dt_times + cz, dt_times, f_cz)

	# combine
	skin_temp = avg_skin_temp +  + 273.15   # [K]

	# check for validity
	if not (1.5 < u_m < 7.6):
		if (1.1 < a*z < 0) and (1 < numpy.exp(b*z) < 6) and (0 < c*z < 4):
			pass
		else:
			raise ValueError('Wind Speed out of range')

	if (-1.1 < a*z < 0) and (1 < numpy.exp(b*z) < 6) and (0 < c*z < 4):
		pass
	else:
		print(a*z, numpy.exp(b*z), c*z)

	return skin_temp

def wind_speed_height_correction(wspd, h1, h2, n=0.1):
	# equation 2.9 in padula, simpolified wind speed correction
	return wspd * (h2 / h1) ** n

op = overpass_date
skt = [skin_tmp(data, dates, headers, op + datetime.timedelta(hours=d), buoy_depth) for d in range(-12, 13)]

plt.figure()
plt.plot(w_temp + 273.15, 'k')
plt.plot(range(12, 37), skt, 'b')
plt.title('24 Hour Water Temperature at Buoy {0} on {1}'.format(buoy_id, overpass_date))
plt.xlabel('Hour (hour 12 is the closest to overpass time)')
plt.ylabel('Water Temperature ' + units[headers.index('WTMP')])
plt.legend(['Bulk Temperature', 'Skin Temperature'])
plt.show()