import os
import sys

from oba_rvtd_deployer import REPORTS_DIR


class FabLogger():
    '''Copied from http://stackoverflow.com/questions/4675728/redirect-stdout-to-a-file-in-python
    '''
    
    def __init__(self, filename=os.path.join(REPORTS_DIR, 'fab.log')):
        self.terminal = sys.stdout
        self.log = open(filename, 'w')
        
    def __getattr__(self, attr): 
        return getattr(self.terminal, attr)

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        

def unix_path_join(dir1, dir2):
    return '{0}/{1}'.format(dir1, dir2)
