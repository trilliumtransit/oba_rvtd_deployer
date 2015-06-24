import sys

from oba_rvtd_deployer.aws import launch_new, tear_down
from oba_rvtd_deployer.gtfs import validate_gtfs, update
from oba_rvtd_deployer.oba import install, deploy, start, copy_gwt


def run_all():
    '''A single script to deploy OBA in one command to a new EC2 instance
    '''
    
    # dl gtfs and validate it
    if validate_gtfs():
        print('GTFS Validation Failed')
        sys.exit()
    
    # setup new EC2 instance
    instance = launch_new()
    
    public_dns_name = instance.public_dns_name
    
    # install OBA
    install(public_dns_name)
    
    # update GTFS, make new bundle
    update(public_dns_name)

    # deploy webapps to tomcat
    deploy(public_dns_name)
    
    # start server
    start(public_dns_name)

    # move GWT files to production webapp dir
    copy_gwt(public_dns_name)
