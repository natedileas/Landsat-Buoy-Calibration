
def csv_to_txt(csv_file, column=1):
    data = []

    with open(csv_file, 'rb') as f:
        for line in f:
            d = line.decode('utf-8', errors='ignore').split(',')
            data.append(d[column].split('/')[-1])

    return data

if __name__=='__main__':
    import argparse

    parser = argparse.ArgumentParser(description='')

    parser.add_argument('csv_files', nargs='+')
    parser.add_argument('-t', '--text', default='modis_scenes.txt')

    args = parser.parse_args()

    with open(args.text, 'w') as f:
        for csv in args.csv_files:
            data = csv_to_txt(csv)
            f.write('\n'.join(data[1:]))