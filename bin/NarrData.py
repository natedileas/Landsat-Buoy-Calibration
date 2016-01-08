import subprocess
import os

def download(cc):
    """ launcher for NARR_py.bash. """
    # check if narr data is already downloaded
    if os.path.exists(os.path.join(cc.scene_dir, 'narr/HGT_1/1000.txt')):
        return 0

    try:
        # begin download of NARR data
        current_dir = os.getcwd()
        if current_dir is not cc.filepath_base:
            os.chdir(cc.filepath_base)

        os.chmod('./bin/NARR_py.bash', 0755)
        subprocess.check_call('chmod u+x ./bin/NARR_py.bash', shell=True)
        
        v = -1
        if cc.verbose:
          v = 0
          
        ret_val = subprocess.call('./bin/NARR_py.bash %s %s' % (cc.scene_id, v), shell=True)
        os.chdir(current_dir)
        
        if ret_val == 1:
            return -1

    except KeyboardInterrupt:
        return -1
    else:
        return 0