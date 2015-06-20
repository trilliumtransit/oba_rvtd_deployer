try: 
    input = raw_input
except NameError: 
    pass
import os
import sys
import time

from fabric.api import env, run, put, cd
from fabric.exceptions import NetworkError

from oba_rvtd_deployer import CONFIG_TEMPLATE_DIR, CONFIG_DIR, REPORTS_DIR
from oba_rvtd_deployer.config import (get_aws_config, 
                                      get_oba_config,
                                      get_gtfs_config)
from oba_rvtd_deployer.util import unix_path_join, FabLogger


class ObaRvtdFab:
    
    aws_conf = get_aws_config()
    gtfs_conf = get_gtfs_config()
    oba_conf = get_oba_config()
    oba_base_folder = oba_conf.get('DEFAULT', 'oba_base_folder')
        
    def __init__(self, host_name):
        '''Constructor for Class.  Sets up fabric environment.
        
        Args:
            host_name (string): ec2 public dns name
        '''
        
        env.host_string = '{0}@{1}'.format(self.aws_conf.get('DEFAULT', 'user'), host_name)
        env.key_filename = [self.aws_conf.get('DEFAULT', 'key_filename')]
        sys.stdout = FabLogger(os.path.join(REPORTS_DIR, 'oba_fab.log'))
        
        max_retries = 4
        num_retries = 0
    
        putty_tried = False
        
        retry = True
        while retry:
            try:
                # SSH into the box here.
                self.test_cmd()
                retry = False
            except NetworkError as e:
                if 'timeout' not in str(e) and not putty_tried:
                    print('The ec2 instance may not work with a windows machine yet.')
                    print('Connecting manually with Putty may resolve this.')
                    print('Please try connecting to the server with Putty, then the rest of this script may work.')
                    input('Press Enter after you have connected using Putty...')
                    putty_tried = True
                    continue
                else:
                    print(e)
                if num_retries > max_retries:
                    raise Exception('Maximum Number of SSH Retries Hit.  Did EC2 instance get configured with ssh correctly?')
                num_retries += 1 
                print('SSH failed, waiting 10 seconds...')
                time.sleep(10)
        
    def test_cmd(self):
        '''Simple command to test if connection works.
        '''
        run('uname')
        
    def install_all(self):
        '''Installs all OneBusAway stuff.
        '''
        self.clone_repo()
        self.install_federation_webapp()
        self.install_api_webapp()
        self.install_webapp()
        
    def clone_repo(self):
        '''Clone the repo and upload some files.
        '''
        
        # clone the repo
        run('git clone {0}'.format(self.oba_conf.get('DEFAULT', 'oba_git_repo')))
        
    def build_webapp(self, data_dict, config_template_file, webapp):
        '''Build a webapp using maven.
        
        Args:
            data_dict (dict): A dict to set the stuff in the config template.
            config_tempalte_file (string): filename of the config template file.
            webapp (string): The name of the webapp to build.
        '''
        temp_data_sources_filename = os.path.join(CONFIG_DIR, 'data-sources.xml')
        
        # get the data sources template
        with open(os.path.join(CONFIG_TEMPLATE_DIR, config_template_file)) as f:
            data_sources_template = f.read()
            
        with open(temp_data_sources_filename, 'w') as f:
            f.write(data_sources_template.format(**data_dict))
            
        put(temp_data_sources_filename, 
            unix_path_join(self.oba_base_folder, webapp))
        
        with cd(self.oba_base_folder):
            run('/usr/local/maven/bin/mvn -am -pl {0} package'.format(webapp))
        
    def install_api_webapp(self):
        '''Installs the api-webapp.
        '''
        
        if self.oba_conf.get('DEFAULT', 'allow_api_test_key') == 'True':
            api_test_xml = '<bean class="org.onebusaway.users.impl.CreateApiKeyAction"><property name="key" value="TEST"/></bean>'
        else:
            api_test_xml = ''
        
        api_config = dict(pg_username=self.oba_conf.get('DEFAULT', 'pg_username'),
                          pg_password=self.oba_conf.get('DEFAULT', 'pg_password'),
                          api_testing=api_test_xml)
        
        self.build_webapp(api_config, 
                          'api-webapp-data-sources.xml',
                          'onebusaway-api-webapp')
        
    def install_federation_webapp(self):
        '''Installs the transit-data-federation-webapp.
        '''
        
        transit_fed_config = dict(pg_username=self.oba_conf.get('DEFAULT', 'pg_username'),
                                  pg_password=self.oba_conf.get('DEFAULT', 'pg_password'),
                                  data_bundle_path='data/bundle',
                                  gtfs_rt_trip_updates_url=self.gtfs_conf.get('DEFAULT', 'gtfs_rt_trip_updates_url'),
                                  gtfs_rt_vehicle_positions_url=self.gtfs_conf.get('DEFAULT', 'gtfs_rt_vehicle_positions_url'),
                                  gtfs_rt_service_alerts_url=self.gtfs_conf.get('DEFAULT', 'gtfs_rt_service_alerts_url'))
        
        self.build_webapp(transit_fed_config, 
                          'transit-data-federation-webapp-data-sources.xml',
                          'onebusaway-transit-data-federation-webapp')
        
    def install_webapp(self):
        '''Installs the webapp.
        '''
        
        webapp_config = dict(pg_username=self.oba_conf.get('DEFAULT', 'pg_username'),
                             pg_password=self.oba_conf.get('DEFAULT', 'pg_password'))
        
        self.build_webapp(webapp_config, 
                          'webapp-data-sources.xml',
                          'onebusaway-webapp')
                        

def install(instance_dns_name=None):
    '''Installs OBA on the EC2 instance.
    '''
    if not instance_dns_name:
        instance_dns_name = input('Enter EC2 public dns name: ')
        
    oba_fab = ObaRvtdFab(instance_dns_name)
    oba_fab.install_all()
            
    
def start():
    '''Start the OBA server on the EC2 instance.
    '''
    pass


def stop():
    '''Stop the OBA server on the EC2 instance.
    '''
    pass
