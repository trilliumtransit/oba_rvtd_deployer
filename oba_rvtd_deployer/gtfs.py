try: 
    input = raw_input
except NameError: 
    pass
from datetime import datetime
import os
import sys
import time

from fabric.api import env, run, put, cd
from fabric.exceptions import NetworkError
from transitfeed.gtfsfactory import GetGtfsFactory
from transitfeed.problems import ProblemReporter, TYPE_WARNING
import requests
import transitfeed

from oba_rvtd_deployer import DL_DIR, REPORTS_DIR
from oba_rvtd_deployer.config import (get_aws_config, 
                                      get_gtfs_config,
                                      get_oba_config)
from oba_rvtd_deployer.feedvalidator import HTMLCountingProblemAccumulator
from oba_rvtd_deployer.util import FabLogger, unix_path_join
from fabric.contrib.files import exists


gtfs_file_name_raw = 'google_transit_{0}.zip'.format(datetime.now().strftime('%Y-%m-%d'))
gtfs_file_name = os.path.join(DL_DIR, gtfs_file_name_raw)


class GtfsFab:
    
    aws_conf = get_aws_config()
    gtfs_conf = get_gtfs_config()
    oba_conf = get_oba_config()
    oba_base_folder = oba_conf.get('DEFAULT', 'oba_base_folder')
    user = aws_conf.get('DEFAULT', 'user')
        
    def __init__(self, host_name):
        '''Constructor for Class.  Sets up fabric environment.
        
        Args:
            host_name (string): ec2 public dns name
        '''
        
        env.host_string = '{0}@{1}'.format(self.user, host_name)
        env.key_filename = [self.aws_conf.get('DEFAULT', 'key_filename')]
        sys.stdout = FabLogger(os.path.join(REPORTS_DIR, 'gtfs_fab.log'))
        
        max_retries = 6
        num_retries = 0
    
        retry = True
        while retry:
            try:
                # SSH into the box here.
                self.test_cmd()
                retry = False
            except NetworkError as e:
                print(e)
                if num_retries > max_retries:
                    raise Exception('Maximum Number of SSH Retries Hit.  Did EC2 instance get configured with ssh correctly?')
                num_retries += 1 
                print('SSH failed (the system may still be starting up), waiting 10 seconds...')
                time.sleep(10)
        
    def test_cmd(self):
        '''Simple command to test if connection works.
        '''
        run('uname')
        
    def update_gtfs(self):
        '''Uploads the downloaded gtfs zip file to the server and builds a new bundle.
        '''
        
        data_dir = unix_path_join('/home', 
                                  self.user,
                                  'data')
        remote_gtfs_file = unix_path_join(data_dir, gtfs_file_name_raw)
        bundle_dir = unix_path_join(data_dir, 'bundle')
        
        # check if data folders exists
        if not exists(data_dir):
            run('mkdir {0}'.format(data_dir))
            
        # remove old gtfs file (if needed)
        if exists(remote_gtfs_file):
            run('rm {0}'.format(remote_gtfs_file))
        
        # upload new file
        put(gtfs_file_name, 'data')
        
        # create new bundle
        bundle_main = '.'.join(['org',
                                'onebusaway',
                                'transit_data_federation',
                                'bundle',
                                'FederatedTransitDataBundleCreatorMain'])
        with cd(unix_path_join(self.oba_conf.get('DEFAULT', 'oba_base_folder'),
                               'onebusaway-transit-data-federation-builder')):
            run('java -classpath .:target/* {0} {1} {2}'.format(bundle_main,
                                                                remote_gtfs_file,
                                                                bundle_dir))


def validate_gtfs():
    '''Download (if needed) and validate the latest static GTFS file.
    
    Returns:
        boolean: True if no errors in GTFS.
    '''
    
    # get gtfs settings
    gtfs_conf = get_gtfs_config()
    
    # Create the `downloads` directory if it doesn't exist
    if not os.path.exists(DL_DIR):
        os.makedirs(DL_DIR)
        
    # Create the `reports` directory if it doesn't exist
    if not os.path.exists(REPORTS_DIR):
        os.makedirs(REPORTS_DIR)
    
    # download gtfs
    print('Downloading GTFS')
    r = requests.get(gtfs_conf.get('DEFAULT', 'gtfs_static_url'), stream=True)
    with open(gtfs_file_name, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024): 
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
                f.flush()
                
    # load gtfs
    print('Validating GTFS')
    gtfs_factory = GetGtfsFactory()
    accumulator = HTMLCountingProblemAccumulator(limit_per_type=50)
    problem_reporter = ProblemReporter(accumulator)
    loader = gtfs_factory.Loader(gtfs_file_name, problems=problem_reporter)
    schedule = loader.Load()
    
    # validate gtfs
    schedule.Validate()
    
    # check for trips with a null value for trip_headsign
    for trip in schedule.GetTripList():
        if trip.trip_headsign == 'null':
            problem_reporter.InvalidValue('trip_headsign', 'null', type=TYPE_WARNING)
            
    # write GTFS report to file
    report_name = 'gtfs_validation_{0}.html'.format(datetime.now().strftime('%Y-%m-%d %H.%M'))
    report_filenmae = os.path.join(REPORTS_DIR, report_name)
    with open(report_filenmae, 'w') as f:
        accumulator.WriteOutput(gtfs_file_name, f, schedule, transitfeed)
        
    print('GTFS validation report written to {0}'.format(report_filenmae))
    
    # post-validation
    gtfs_validated = True
    num_errors = accumulator.ErrorCount()
    if num_errors > 0:
        gtfs_validated = False
        print('{0} errors in GTFS data'.format(num_errors))
        
    num_warnings = accumulator.WarningCount()
    if num_warnings > 0:
        print('{0} warnings about GTFS data'.format(num_warnings))
        
    if 'ExpirationDate' in accumulator.ProblemListMap(TYPE_WARNING).keys():
        start_date, end_date = schedule.GetDateRange()
        last_service_day = datetime(*(time.strptime(end_date, "%Y%m%d")[0:6]))
        if last_service_day < datetime.now():
            print('GTFS Feed has expired.')
            gtfs_validated = False
        
    return gtfs_validated


def update(instance_dns_name=None, refresh_gtfs_file=False):
    '''Update the gtfs file on the EC2 instance and tell OBA to create a new bundle.
    
    This assumes that onebusaway-transit-data-federation-builder has been installed on the server.
    It will also download the gtfs file if it does not find it in the local downloads folder.
    
    Args:
        instance_dns_name (string, default=None): The EC2 instance to upload the gtfs to.
        refresh_gtfs_file (boolean, default=False): Whether or not to refetch and validate the gtfs file.
    '''
    
    if not os.path.exists(gtfs_file_name) or refresh_gtfs_file:
        if not validate_gtfs():
            raise Exception('GTFS static file validation Failed.')
        
    if not instance_dns_name:
        instance_dns_name = input('Enter EC2 public dns name: ')
        
    gtfs_fab = GtfsFab(instance_dns_name)
    gtfs_fab.update_gtfs()
