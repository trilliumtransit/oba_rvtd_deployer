from datetime import datetime
import os

from transitfeed.gtfsfactory import GetGtfsFactory
from transitfeed.problems import ProblemReporter, TYPE_WARNING
import requests
import transitfeed

from oba_rvtd_deployer import DL_DIR, REPORTS_DIR
from oba_rvtd_deployer.config import get_gtfs_config
from oba_rvtd_deployer.feedvalidator import HTMLCountingProblemAccumulator


gtfs_file_name = 'google_transit_{0}.zip'.format(datetime.now().strftime('%Y-%m-%d'))
gtfs_file_name = os.path.join(DL_DIR, gtfs_file_name)


def validate_gtfs():
    '''Download (if needed) and validate the latest static GTFS file.
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
    gtfs_fatal_validation = False
    num_errors = accumulator.ErrorCount()
    if num_errors > 0:
        gtfs_fatal_validation = True
        print('{0} errors in GTFS data'.format(num_errors))
        
    num_warnings = accumulator.WarningCount()
    if num_warnings > 0:
        print('{0} warnings about GTFS data'.format(num_warnings))
        
    if 'ExpirationDate' in accumulator.ProblemListMap(TYPE_WARNING).keys():
        print('GTFS Feed has expired.')
        gtfs_fatal_validation = True
        
    return gtfs_fatal_validation


def update():
    '''Update the gtfs file on the EC2 instance and tell OBA to create a new bundle.
    '''
    pass
