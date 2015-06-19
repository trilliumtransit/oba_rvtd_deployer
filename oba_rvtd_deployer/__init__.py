import os

__import__('pkg_resources').declare_namespace(__name__)


BASE_DIR = os.path.split(os.path.dirname(__file__))[0]
CONFIG_TEMPLATE_DIR = os.path.join(BASE_DIR, 'config_templates')
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
DATA_DIR = os.path.join(BASE_DIR, 'data')
DL_DIR = os.path.join(DATA_DIR, 'downloads')
REPORTS_DIR = os.path.join(DATA_DIR, 'reports')


def run_all():
    '''A single script to deploy OBA in one command to a new EC2 instance
    '''
    
    # dl gtfs and validate it
    
    # setup new EC2 instance
    
    # install OBA
    
    # update GTFS, make new bundle
    
    # start server
    pass
