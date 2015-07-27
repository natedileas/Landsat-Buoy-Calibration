import subprocess
import os

class NarrData(object):
    def __init__(self, other):
        self.scene_id = other._scene_id

        self.filepath_base = other.filepath_base

        if other.verbose:
            self.verbose = 0
        else:
            self.verbose = -1

    def start_download(self):
        try:
            # begin download of NARR data
            current_dir = os.getcwd()
            os.chdir(self.filepath_base)
            os.chmod('./bin/NARR_py.bash', 0755)
            subprocess.check_call('chmod u+x ./bin/NARR_py.bash', shell=True)
            ret_val = subprocess.call('./bin/NARR_py.bash %s %s' % (self.scene_id,
                            self.verbose), shell=True)
            os.chdir(current_dir)
            
            if ret_val == 1:
                return -1

        except KeyboardInterrupt:
            return -1
        else:
            return 0
