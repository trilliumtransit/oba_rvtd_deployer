try: 
    input = raw_input
except NameError: 
    pass
import os
import sys
import time

from fabric.api import env, run, put, cd, sudo
from fabric.contrib.files import exists
from fabric.exceptions import NetworkError

from oba_rvtd_deployer import REPORTS_DIR, CONFIG_DIR, CONFIG_TEMPLATE_DIR
from oba_rvtd_deployer.config import (get_aws_config, 
                                      get_oba_config,
                                      get_gtfs_config, get_watchdog_config)
from oba_rvtd_deployer.fab_crontab import crontab_update
from oba_rvtd_deployer.util import unix_path_join, FabLogger, write_template


class ObaRvtdFab:
    
    aws_conf = get_aws_config()
    gtfs_conf = get_gtfs_config()
    oba_conf = get_oba_config()
    oba_base_folder = oba_conf.get('DEFAULT', 'oba_base_folder')
    user = aws_conf.get('DEFAULT', 'user')
    config_dir = unix_path_join('/home', user, 'conf')
    script_dir = unix_path_join('/home', user, 'scripts')
        
    def __init__(self, host_name):
        '''Constructor for Class.  Sets up fabric environment.
        
        Args:
            host_name (string): ec2 public dns name
        '''
        
        env.host_string = '{0}@{1}'.format(self.user, host_name)
        env.key_filename = [self.aws_conf.get('DEFAULT', 'key_filename')]
        sys.stdout = FabLogger(os.path.join(REPORTS_DIR, 'oba_fab.log'))
        
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
        
    def install_all(self):
        '''Installs all OneBusAway stuff.
        '''
        self.clone_repo()
        self.install_federation_webapp()
        self.install_api_webapp()
        self.install_sms_webapp()
        self.install_webapp()
        
    def clone_repo(self):
        '''Clone the repo and upload some files.
        '''
        
        # clone the repo
        run('git clone {0}'.format(self.oba_conf.get('DEFAULT', 'oba_git_repo')))
        
        with cd(self.oba_base_folder):
            run('git checkout {0}'.format(self.oba_conf.get('DEFAULT', 'oba_git_branch')))
            run('/usr/local/maven/bin/mvn clean install')
        
    def build_webapp(self, data_dict, config_template_file, webapp):
        '''Build a webapp using maven.
        
        Args:
            data_dict (dict): A dict to set the stuff in the config template.
            config_tempalte_file (string): filename of the config template file.
            webapp (string): The name of the webapp to build.
        '''
                   
        # upload the data sources file to the project
        put(write_template(data_dict, 
                           config_template_file, 
                           'data-sources.xml'), 
            unix_path_join(self.oba_base_folder,
                           webapp,
                           'src',
                           'main',
                           'resources'))
        
        # build the project using maven
        with cd(self.oba_base_folder):
            run('/usr/local/maven/bin/mvn -am -pl {0} package'.format(webapp))
        
    def install_api_webapp(self):
        '''Installs the api-webapp.
        '''
        
        if self.oba_conf.get('DEFAULT', 'allow_api_test_key').lower() == 'true':
            api_test_xml = '<bean class="org.onebusaway.users.impl.CreateApiKeyAction"><property name="key" value="TEST"/></bean>'
        else:
            api_test_xml = ''
        
        api_config = dict(api_testing=api_test_xml,
                          elastic_ip=self.aws_conf.get('DEFAULT', 'elastic_ip'),
                          pg_password=self.oba_conf.get('DEFAULT', 'pg_password'),
                          pg_username=self.oba_conf.get('DEFAULT', 'pg_username'))
        
        self.build_webapp(api_config, 
                          'api-webapp-data-sources.xml',
                          'onebusaway-api-webapp')
        
    def install_federation_webapp(self):
        '''Installs the transit-data-federation-webapp.
        '''
        
        transit_fed_config = dict(pg_username=self.oba_conf.get('DEFAULT', 'pg_username'),
                                  pg_password=self.oba_conf.get('DEFAULT', 'pg_password'),
                                  data_bundle_path=unix_path_join('/home',
                                                                  self.user,
                                                                  'data',
                                                                  'bundle'),
                                  gtfs_rt_trip_updates_url=self.gtfs_conf.get('DEFAULT', 'gtfs_rt_trip_updates_url'),
                                  gtfs_rt_vehicle_positions_url=self.gtfs_conf.get('DEFAULT', 'gtfs_rt_vehicle_positions_url'),
                                  gtfs_rt_service_alerts_url=self.gtfs_conf.get('DEFAULT', 'gtfs_rt_service_alerts_url'))
        
        self.build_webapp(transit_fed_config, 
                          'transit-data-federation-webapp-data-sources.xml',
                          'onebusaway-transit-data-federation-webapp')
        
    def install_sms_webapp(self):
        '''Installs the sms-webapp.
        '''
        
        sms_config = dict(pg_username=self.oba_conf.get('DEFAULT', 'pg_username'),
                          pg_password=self.oba_conf.get('DEFAULT', 'pg_password'))
        
        self.build_webapp(sms_config, 
                          'sms-webapp-data-sources.xml',
                          'onebusaway-sms-webapp')
        
    def install_webapp(self):
        '''Installs the webapp.
        '''
        
        webapp_config = dict(pg_username=self.oba_conf.get('DEFAULT', 'pg_username'),
                             pg_password=self.oba_conf.get('DEFAULT', 'pg_password'),
                             elastic_ip=self.aws_conf.get('DEFAULT', 'elastic_ip'))
        
        self.build_webapp(webapp_config, 
                          'webapp-data-sources.xml',
                          'onebusaway-webapp')
        
    def deploy_all(self):
        '''Deploys each webapp (copies to tomcat webapps).
        '''
        
        # copy the war files to tomcat for each webapp
        tomcat_webapp_dir = unix_path_join('/home',
                                           self.user,
                                           'tomcat',
                                           'webapps')
        for webapp in ['onebusaway-transit-data-federation-webapp',
                       'onebusaway-api-webapp',
                       'onebusaway-sms-webapp',
                       'onebusaway-webapp']:
            run('cp {0} {1}'.format(unix_path_join('/home',
                                                   self.user,
                                                   self.oba_base_folder,
                                                   webapp,
                                                   'target',
                                                   webapp + '.war'),
                                    tomcat_webapp_dir))
            
    def start_servers(self):
        '''Starts tomcat and xwiki servers.
        '''
        
        # start servers
        run('set -m; /home/{0}/tomcat/bin/startup.sh'.format(self.user))
        # writing output to /dev/null because logs are already written to /usr/local/xwiki/data/logs
        sudo('set -m; sudo nohup /usr/local/xwiki/start_xwiki.sh -p 8081 > /dev/null &')
        
    def stop_servers(self):
        '''Stops tomcat and xwiki servers.
        '''
        
        # stop servers immediately
        run('set -m; /home/{0}/tomcat/bin/shutdown.sh'.format(self.user))
        sudo('set -m; /usr/local/xwiki/stop_xwiki.sh -p 8081')
        
    def install_watchdog(self):
        '''Configures and uploads watchdog script.  Adds cron task to run it.
        '''
        
        # ensure watchdog config exists by retrieving it
        get_watchdog_config()
        
        # ensure watchdog .py file is in config directory
        oba_script_file = os.path.join(CONFIG_DIR, 'check_oba.py')
        if not os.path.exists(oba_script_file):
            print('Watchdog python script does not exist in config directory.')
            print('Please create it and set the appropriate location of the watchdog.ini file.')
            return
        
        # ensure script and config folder exists
        if not exists(self.config_dir):
            run('mkdir {0}'.format(self.config_dir))
            
        if not exists(self.script_dir):
            run('mkdir {0}'.format(self.script_dir))
            
        # upload watchdog script (remove it if needed)
        remote_script_file = unix_path_join(self.script_dir, 'check_oba.py')
        if exists(remote_script_file):
            sudo('rm -rf {0}'.format(remote_script_file))
            
        put(oba_script_file, self.script_dir)
        
        # upload watchdog config (remove it if needed)
        remote_config_file = unix_path_join(self.config_dir, 'watchdog.ini')
        if exists(remote_config_file):
            sudo('rm -rf {0}'.format(remote_config_file))
            
        put(os.path.join(CONFIG_DIR, 'watchdog.ini'), self.config_dir)
        
        # update/insert cron to run script
        with open(os.path.join(CONFIG_TEMPLATE_DIR, 'watchdog_crontab')) as f:
            refresh_cron_template = f.read()
            
        cron_settings = dict(cron_email=self.aws_conf.get('DEFAULT', 'cron_email'),
                             watchdog_script=remote_script_file)
        cron = refresh_cron_template.format(**cron_settings)
            
        crontab_update(cron, 'watchdog_cron')        
                    

def install(instance_dns_name=None):
    '''Installs OBA on the EC2 instance.
    
    Args:
        instance_dns_name (string, default=None): The EC2 instance to deploy to.
    '''
    
    if not instance_dns_name:
        instance_dns_name = input('Enter EC2 public dns name: ')
        
    oba_fab = ObaRvtdFab(instance_dns_name)
    oba_fab.install_all()
    
    
def deploy(instance_dns_name=None):
    '''Deploys the webapps to Tomcat.
    
    Args:
        instance_dns_name (string, default=None): The EC2 instance to deploy to.
    '''
    
    if not instance_dns_name:
        instance_dns_name = input('Enter EC2 public dns name: ')
        
    oba_fab = ObaRvtdFab(instance_dns_name)
    oba_fab.deploy_all()
            
    
def start(instance_dns_name=None):
    '''Start the OBA server on the EC2 instance.
    
    Args:
        instance_dns_name (string, default=None): The EC2 instance to deploy to.
    '''
    
    if not instance_dns_name:
        instance_dns_name = input('Enter EC2 public dns name: ')
        
    oba_fab = ObaRvtdFab(instance_dns_name)
    oba_fab.start_servers()


def stop(instance_dns_name=None):
    '''Stop the OBA server on the EC2 instance.
    
    Args:
        instance_dns_name (string, default=None): The EC2 instance to deploy to.
    '''
    
    if not instance_dns_name:
        instance_dns_name = input('Enter EC2 public dns name: ')
        
    oba_fab = ObaRvtdFab(instance_dns_name)
    oba_fab.stop_servers()


def copy_gwt(instance_dns_name=None):
    '''Copy GWT files on OBA server on the EC2 instance.
    
    Args:
        instance_dns_name (string, default=None): The EC2 instance to deploy to.
    '''
    pass


def install_watchdog(instance_dns_name=None):
    '''Installs OBA on the EC2 instance.
    
    Args:
        instance_dns_name (string, default=None): The EC2 instance to deploy to.
    '''
    
    if not instance_dns_name:
        instance_dns_name = input('Enter EC2 public dns name: ')
        
    oba_fab = ObaRvtdFab(instance_dns_name)
    oba_fab.install_watchdog()
