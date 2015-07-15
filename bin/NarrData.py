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
            # TODO have intelligent paths
            narr_py_path = os.path.join(self.filepath_base, 'bin/NARR_py.bash')
            subprocess.check_call('chmod u+x '+narr_py_path, shell=True)
            subprocess.call('./bin/NARR_py.bash %s %s' % (self.scene_id,
                            self.verbose), shell=True)
        except KeyboardInterrupt:
            return -1
        else:
            return 0   # potentially thread out removal of scripts
            # and check for successful download before exiting
