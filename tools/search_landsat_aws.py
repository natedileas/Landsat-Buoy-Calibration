
def search_landsat_aws(landsat_id, name='scene_list.txt'):

	with open(name, 'r') as f:
		header = f.readline().split(',')

		for i, line in enumerate(f):
			s = line.split(',')
			if landsat_id == s[0] or landsat_id == s[1]:

				return s, header

		return i

if __name__ == '__main__':
	print(search_landsat_aws('LC08_L1TP_017030_20150916_20170225_01_T1'))
	print(search_landsat_aws('LC08_L1TP_017030_20170921_20171012_01_T1'))
	print(search_landsat_aws('LC08_L1TP_017030_20140406_20170307_01_T1'))
	print(search_landsat_aws('LC80160302013150LGN01'))
	