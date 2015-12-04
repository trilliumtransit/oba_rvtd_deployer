try: 
    input = raw_input
except NameError: 
    pass
import os
import sys
import time

import boto.ec2
from fabric.api import env, run, sudo, cd, put
from fabric.context_managers import settings
from fabric.contrib.files import exists
from fabric.exceptions import NetworkError

from oba_rvtd_deployer import REPORTS_DIR, CONFIG_TEMPLATE_DIR
from oba_rvtd_deployer.config import get_aws_config, get_oba_config
from oba_rvtd_deployer.fab_crontab import crontab_update
from oba_rvtd_deployer.util import FabLogger, write_template, unix_path_join


def get_aws_connection():
    '''Connect to AWS.
    
    Returns:
        boto.ec2.connection.EC2Connection: Connection to region.
    '''
    
    print('Connecting to AWS')
    aws_conf = get_aws_config()
    return boto.ec2.connect_to_region(aws_conf.get('DEFAULT', 'region'),
                                      aws_access_key_id=aws_conf.get('DEFAULT', 'aws_access_key_id'),
                                      aws_secret_access_key=aws_conf.get('DEFAULT', 'aws_secret_access_key'))


def launch_new():
    '''Launch a new EC2 instance installing an OBA instance
    '''
    
    # connect to AWS and launch new instance
    aws_conf = get_aws_config()
    conn = get_aws_connection()
    
    print('Preparing volume')
    dev_xvda = boto.ec2.blockdevicemapping.EBSBlockDeviceType()
    dev_xvda.size = aws_conf.get('DEFAULT', 'volume_size')
    dev_xvda.delete_on_termination = True
    block_device_map = boto.ec2.blockdevicemapping.BlockDeviceMapping()
    block_device_map['/dev/xvda'] = dev_xvda 
    
    print('Launching new instance')
    reservation = conn.run_instances(aws_conf.get('DEFAULT', 'ami_id'),
                                     instance_type=aws_conf.get('DEFAULT', 'instance_type'),
                                     key_name=aws_conf.get('DEFAULT', 'key_name'),
                                     security_groups=aws_conf.get('DEFAULT', 'security_groups').split(','),
                                     block_device_map=block_device_map)
    
    # Get the instance
    instance = reservation.instances[0]
    
    # Check if it's up and running a specified maximum number of times
    max_retries = 10
    num_retries = 0
    
    # Check up on its status every so often
    status = instance.update()
    while status == 'pending':
        if num_retries > max_retries:
            tear_down(instance.id, conn)
            raise Exception('Maximum Number of Instance Retries Hit.  Did EC2 instance spawn correctly?')
        num_retries += 1 
        print('Instance pending, waiting 10 seconds...')
        time.sleep(10)
        status = instance.update()
    
    if status == 'running':
        instance.add_tag("Name", aws_conf.get('DEFAULT', 'instance_name'))
        instance.add_tag("Client", aws_conf.get('DEFAULT', 'client_name'))
    else:
        print('Instance status: ' + status)
        return None
    
    # Now that the status is running, it's not yet launched. 
    # The only way to tell if it's fully up is to try to SSH in.
    aws_system = AwsFab(instance.public_dns_name)
    
    # If we've reached this point, the instance is up and running.
    print('SSH working')
    aws_system.set_timezone()
    aws_system.turn_off_ipv6()
    aws_system.install_pg()
    aws_system.update_system()
    aws_system.install_all()
    
    return instance


class AwsFab:
    
    aws_conf = get_aws_config()
    oba_conf = get_oba_config()
    user = aws_conf.get('DEFAULT', 'user')
    config_dir = unix_path_join('/home', user, 'conf')
    
    def __init__(self, host_name):
        '''Constructor for Class.  Sets up fabric environment.
        
        Args:
            host_name (string): ec2 public dns name
        '''
        
        env.host_string = '{0}@{1}'.format(self.user, host_name)
        env.key_filename = [self.aws_conf.get('DEFAULT', 'key_filename')]
        sys.stdout = FabLogger(os.path.join(REPORTS_DIR, 'aws_fab.log'))
        
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
        '''A test command to see if everything is running ok.
        '''
        
        run('uname')
        
    def update_system(self):
        '''Updates the instance with the latest patches and upgrades.
        '''
        
        sudo('yum -y update')
        
    def turn_off_ipv6(self):
        '''Edits the networking settings to turn off ipv6.
        
        Credit to CDSU user on http://blog.acsystem.sk/linux/rhel-6-centos-6-disabling-ipv6-in-system
        '''
        
        # unfortunately, this requires sudo access
        with settings(warn_only=True):
            sudo('echo "net.ipv6.conf.default.disable_ipv6=1" >> /etc/sysctl.conf')
            sudo('echo "net.ipv6.conf.all.disable_ipv6 = 1" >> /etc/sysctl.conf')
            sudo('sysctl -p')
    
    def install_all(self, exclude_pg=True):
        '''Method to install all stuff on machine (except OneBusAway).
        
        Args:
            exclude_pg (bool, default=True): skips installation of pg.  Typically this is done right after instance startup.
        '''
        
        # self.install_helpers()
        if not exclude_pg:
            self.install_pg()
        self.set_timezone()
        self.install_custom_monitoring()
        self.install_git()
        self.install_jdk()
        self.install_maven()
        self.install_tomcat()
        self.install_xwiki()
        
    def set_timezone(self):
        '''Changes the machine's localtime to the desired timezone.
        '''
        
        with cd('/etc'):
            sudo('rm -rf localtime')
            sudo('ln -s {0} localtime'.format(self.aws_conf.get('DEFAULT', 'timezone')))        
        
    def install_custom_monitoring(self):
        '''Installs a custom monitoring script to monitor memory and disk utilization.
        '''
        
        # install helpers
        sudo('yum -y install perl-DateTime perl-Sys-Syslog perl-LWP-Protocol-https')
        
        # dl scripts
        run('wget http://aws-cloudwatch.s3.amazonaws.com/downloads/CloudWatchMonitoringScripts-1.2.1.zip')
        sudo('unzip CloudWatchMonitoringScripts-1.2.1.zip -d /usr/local')
        run('rm CloudWatchMonitoringScripts-1.2.1.zip')
        
        # prepare the monitoring crontab        
        with open(os.path.join(CONFIG_TEMPLATE_DIR, 'monitoring_crontab')) as f:
            cron = f.read()
        
        cron_settings = dict(aws_access_key_id=self.aws_conf.get('DEFAULT', 'aws_access_key_id'),
                             aws_secret_key=self.aws_conf.get('DEFAULT', 'aws_secret_access_key'),
                             cron_email=self.aws_conf.get('DEFAULT', 'cron_email'))  
        aws_logging_cron = cron.format(**cron_settings)
            
        # start crontab for aws monitoring
        crontab_update(aws_logging_cron, 'aws_monitoring')
        
    def install_helpers(self):
        '''Installs various utilities (typically not included with CentOS).
        '''
        
        sudo('yum -y install wget')
        sudo('yum -y install unzip')
    
    def install_git(self):
        '''Installs git.
        '''
        
        sudo('yum -y install git')
        
    def install_jdk(self):
        '''Installs jdk devel, so maven is happy.
        '''
        
        sudo('yum -y install java-1.7.0-openjdk java-1.7.0-openjdk-devel')
        
    def install_maven(self):
        '''Downloads and installs maven.
        '''
        
        # download and extract maven
        run('wget http://mirror.symnds.com/software/Apache/maven/maven-3/3.3.3/binaries/apache-maven-3.3.3-bin.tar.gz')
        sudo('tar xzf apache-maven-3.3.3-bin.tar.gz -C /usr/local')
        run('rm apache-maven-3.3.3-bin.tar.gz')
        with cd('/usr/local'):
            sudo('ln -s apache-maven-3.3.3 maven')
        
        # check that mvn command works
        run('/usr/local/maven/bin/mvn -version')
        
    def upload_pg_hba_conf(self, local_method):
        '''Overwrites pg_hba.conf with specified local method.
        '''
        
        remote_data_folder = '/var/lib/pgsql9/data'
        remote_pg_hba_conf = '/var/lib/pgsql9/data/pg_hba.conf'
        
        sudo('rm -rf {0}'.format(remote_pg_hba_conf))
        
        if not exists(self.config_dir):
            run('mkdir {0}'.format(self.config_dir))
        
        put(write_template(dict(local_method=local_method), 'pg_hba.conf'),
            self.config_dir)
        
        sudo('mv {0} {1}'.format(unix_path_join(self.config_dir, 'pg_hba.conf'),
                                 remote_data_folder))
        
        sudo('chmod 600 {0}'.format(remote_pg_hba_conf))
        sudo('chgrp postgres {0}'.format(remote_pg_hba_conf))
        sudo('chown postgres {0}'.format(remote_pg_hba_conf))
        
    def install_pg(self):
        '''Configures PostgreSQL for immediate use by OneBusAway.
        '''
        
        # install it
        sudo('yum -y install postgresql postgresql-server')
        
        # initialize db
        sudo('service postgresql initdb')
        
        # edit pg_hba for db initialization
        self.upload_pg_hba_conf('trust')
        
        # start postgersql server
        sudo('service postgresql start')
        
        # run init sql
        db_setup_dict = dict(pg_username=self.oba_conf.get('DEFAULT', 'pg_username'),
                             pg_password=self.oba_conf.get('DEFAULT', 'pg_password'),
                             pg_role=self.oba_conf.get('DEFAULT', 'pg_role'))
        
        if not exists(self.config_dir):
            run('mkdir {0}'.format(self.config_dir))
        
        put(write_template(db_setup_dict, 'init.sql'), self.config_dir)
        
        init_sql_filename = unix_path_join(self.config_dir, 'init.sql')
        sudo('psql -U postgres -f {0}'.format(init_sql_filename))
        
        sudo('rm -rf {0}'.format(init_sql_filename))
        
        # switch to more secure pg_hba.conf
        self.upload_pg_hba_conf('md5')
        
        # start postgersql server
        sudo('service postgresql restart')
        
        # start postgresql on boot
        sudo('chkconfig postgresql on')
        
    def install_tomcat(self):
        '''Configures Tomcat on EC2 instance.
        
        Unlinke other items, this is placed in /home/{user} directory,
        so that it can be restarted with cron to refresh gtfs updates.
        '''
        
        # get tomcat from direct download
        run('wget http://mirror.cc.columbia.edu/pub/software/apache/tomcat/tomcat-7/v7.0.65/bin/apache-tomcat-7.0.65.tar.gz')
        
        # move to a local area for better organization
        run('tar xzf apache-tomcat-7.0.65.tar.gz')
        run('rm -rf apache-tomcat-7.0.65.tar.gz')
        run('mv apache-tomcat-7.0.65 tomcat')
                    
        # add logging rotation for catalina.out
        put(write_template(dict(user=self.user), 'tomcat_catalina_out'), '/etc/logrotate.d', True)
        
        # add init.d script
        put(write_template(dict(user=self.user), 'tomcat_init.d'), '/etc/init.d', True)
        with cd('/etc/init.d'):
            sudo('mv tomcat_init.d tomcat')
            sudo('chmod 755 tomcat')
            sudo('chown root tomcat')
            sudo('chgrp root tomcat')
            sudo('chkconfig --add tomcat')
            
    def install_xwiki(self):
        
        run('wget http://download.forge.ow2.org/xwiki/xwiki-enterprise-jetty-hsqldb-7.3.zip')
        
        # move to a local area for better organization
        sudo('unzip xwiki-enterprise-jetty-hsqldb-7.3.zip -d /usr/local')
        run('rm xwiki-enterprise-jetty-hsqldb-7.3.zip')
        
        with cd('/usr/local'):
            sudo('ln -s xwiki-enterprise-jetty-hsqldb-7.3 xwiki')
            
        # add init.d script
        put(os.path.join(CONFIG_TEMPLATE_DIR, 'xwiki_init.d'), '/etc/init.d', True)
        with cd('/etc/init.d'):
            sudo('mv xwiki_init.d xwiki')
            sudo('chmod 755 xwiki')
            sudo('chown root xwiki')
            sudo('chgrp root xwiki')
            sudo('chkconfig --add xwiki')
        

def tear_down(instance_id=None, conn=None):
    '''Terminates a EC2 instance and deletes all associated volumes.
    
    Args:
        instance_id (string): The ec2 instance id to terminate.
        conn (boto.ec2.connection.EC2Connection): Connection to region.
    '''
    
    if not instance_id:
        instance_id = input('Enter instance id: ')
    
    if not conn:
        conn = get_aws_connection()
        
    volumes = conn.get_all_volumes(filters={'attachment.instance-id': [instance_id]})
        
    print('Terminating instance')
    conn.terminate_instances([instance_id])
    
    aws_conf = get_aws_config()
    if aws_conf.get('DEFAULT', 'delete_volumes_on_tear_down') == 'true':
            
        max_wait_retries = 12
        
        print('Deleting volume(s) associated with instance')
        for volume in volumes:
            volume_deleted = False
            num_retries = 0
            while not volume_deleted:
                try:
                    conn.delete_volume(volume.id)
                    volume_deleted = True
                except Exception as e:
                    if num_retries >= max_wait_retries:
                        raise e
                    print('Waiting for volume to become detached from instance.  Waiting 10 seconds...')
                    time.sleep(10)
