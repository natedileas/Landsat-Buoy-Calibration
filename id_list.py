#list.py
import sys
import os
import re
from collections import OrderedDict

def id_list(directory):
    a = os.listdir(directory)
    d = []
    
    with open('./logs/output.txt', 'r') as f:
        output = f.read()


    LID = re.compile('^L[CE][78]\d*\w\w\w0[0-5]')
    
    for file in a:
        match = re.match(LID, file)
        if match:   # if it matches the pattern
            if not str(match.group()) in output:
                d.append(match.group())
            
    #remove duplicates
    ids = list(OrderedDict.fromkeys(d))
    
    #remove unwated path/rows, these are jpl buoy scenes
    wrs2s = ['042033', '137207', '140211']
    scene_IDs = 0
    for wrs2 in wrs2s:
        scene_IDs = [sid for sid in ids if not wrs2 in sid]
    
    #print scene_IDs
    print len(scene_IDs)
    
    return scene_IDs
    
if __name__ == '__main__':
    print id_list('./data/landsat')