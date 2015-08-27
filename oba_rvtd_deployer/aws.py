try: 
    input = raw_input
except NameError: 
    pass
import os
import sys
import time

import boto.ec2
from fabric.api import env, run, sudo, cd, put
from fabric.exceptions import NetworkError

from oba_rvtd_deployer import REPORTS_DIR, CONFIG_TEMPLATE_DIR, CONFIG_DIR
from oba_rvtd_deployer.config import get_aws_config
from oba_rvtd_deployer.fab_crontab import crontab_update
from oba_rvtd_deployer.util import FabLogger


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
    else:
        print('Instance status: ' + status)
        return None
    
    # Now that the status is running, it's not yet launched. 
    # The only way to tell if it's fully up is to try to SSH in.
    num_retries = 0
    aws_system = AwsFab(instance.public_dns_name,
                        aws_conf.get('DEFAULT', 'user'),
                        aws_conf.get('DEFAULT', 'key_filename'))
    
    if status == "running":
        retry = True
        while retry:
            try:
                # SSH into the box here.
                aws_system.test_cmd()
                retry = False
            except NetworkError as e:
                print(e)
                if num_retries > max_retries:
                    tear_down(instance.id, conn)
                    raise Exception('Maximum Number of SSH Retries Hit.  Did EC2 instance get configured with ssh correctly?')
                num_retries += 1 
                print('SSH failed (the system may still be starting up), waiting 10 seconds...')
                time.sleep(10)
    
    # If we've reached this point, the instance is up and running.
    print('SSH working')
    aws_system.turn_off_ipv6()
    aws_system.install_pg()
    aws_system.update_system()
    aws_system.install_all()
    
    return instance


class AwsFab:
    
    aws_conf = get_aws_config()
    
    def __init__(self, host_name, user, key_filename):
        '''Constructor for Class.  Sets up fabric environment.
        
        Args:
            host_name (string): ec2 public dns name
            user (string): ec2 username
            key_filename (string): file location for .pem file
        '''
        
        env.host_string = '{0}@{1}'.format(user, host_name)
        env.key_filename = [key_filename]
        sys.stdout = FabLogger(os.path.join(REPORTS_DIR, 'aws_fab.log'))
        
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
        print('Please ssh as root onto the machine and follow the instructions in the section "Disabling IPv6".')
        input('Press enter to continue...')
        # run('sudo su')
        # run('echo "net.ipv6.conf.default.disable_ipv6=1" >> /etc/sysctl.conf')
        # run('echo "net.ipv6.conf.all.disable_ipv6 = 1" >> /etc/sysctl.conf')
        # run('sysctl -p')
        # run('exit')
    
    def install_all(self, exclude_pg=True):
        '''Method to install all stuff on machine (except OneBusAway).
        
        Args:
            exclude_pg (bool, default=True): skips installation of pg.  Typically this is done right after instance startup.
        '''
        
        # self.install_helpers()
        if not exclude_pg:
            self.install_pg()
        self.install_custom_monitoring()
        self.install_git()
        self.install_jdk()
        self.install_maven()
        self.install_tomcat()
        self.install_xwiki()
        
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
        
    def install_pg(self):
        '''Configures PostgreSQL for immediate use by OneBusAway.
        '''
        
        # install it
        sudo('yum -y install postgresql postgresql-server')
        
        # initialize db
        sudo('service postgresql initdb')
        
        # manually edit pg_hba.conf
        print('Please ssh as root onto the machine and follow the instructions in the section "EC2 PostgreSQL Setup".')
        input('Press enter to continue...')
        
        # start postgresql on boot
        sudo('chkconfig postgresql on')
        
    def install_tomcat(self):
        '''Configures Tomcat on EC2 instance.
        '''
        
        # get tomcat from direct download
        sudo('wget http://mirror.cogentco.com/pub/apache/tomcat/tomcat-7/v7.0.63/bin/apache-tomcat-7.0.63.tar.gz')
        
        # move to a local area for better organization
        sudo('sudo tar xzf apache-tomcat-7.0.63.tar.gz -C /usr/local')
        run('rm -rf apache-tomcat-7.0.63.tar.gz')
        with cd('/usr/local'):
            sudo('ln -s apache-tomcat-7.0.63 tomcat')
            
        # allow copying of files to webapp dir
        with cd('/usr/local/tomcat'):
            sudo('chmod 766 webapps')
            
        # add logging rotation for catalina.out
        put(os.path.join(CONFIG_TEMPLATE_DIR, 'tomcat_catalina_out'), '/etc/logrotate.d', True)
        
        # add init.d script
        put(os.path.join(CONFIG_TEMPLATE_DIR, 'tomcat_init.d'), '/etc/init.d', True)
        with cd('/etc/init.d'):
            sudo('mv tomcat_init.d tomcat')
            sudo('chmod 755 tomcat')
            sudo('chown root tomcat')
            sudo('chgrp root tomcat')
            sudo('chkconfig --add tomcat')
            
    def install_xwiki(self):
        
        run('wget http://download.forge.ow2.org/xwiki/xwiki-enterprise-jetty-hsqldb-7.1.1.zip')
        
        # move to a local area for better organization
        sudo('unzip xwiki-enterprise-jetty-hsqldb-7.1.1.zip -d /usr/local')
        run('rm xwiki-enterprise-jetty-hsqldb-7.1.1.zip')
        
        with cd('/usr/local'):
            sudo('ln -s xwiki-enterprise-jetty-hsqldb-7.1.1 xwiki')
            
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
