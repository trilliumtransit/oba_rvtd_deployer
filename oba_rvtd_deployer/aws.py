try: 
    input = raw_input
except NameError: 
    pass
import time

import boto.ec2
from fabric.api import env, run, sudo, cd
from fabric.exceptions import NetworkError

from oba_rvtd_deployer.config import get_aws_config


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
    print('Launching new instance')
    reservation = conn.run_instances(aws_conf.get('DEFAULT', 'ami_id'),
                                     instance_type=aws_conf.get('DEFAULT', 'instance_type'),
                                     key_name=aws_conf.get('DEFAULT', 'key_name'),
                                     security_groups=aws_conf.get('DEFAULT', 'security_groups').split(','))
    
    # Get the instance
    instance = reservation.instances[0]
    
    # Check if it's up and running a specified maximum number of times
    max_retries = 3
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
    putty_tried = False
    
    if status == "running":
        retry = True
        while retry:
            try:
                # SSH into the box here. I personally use fabric
                aws_system.test_cmd()
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
                    tear_down(instance.id, conn)
                    raise Exception('Maximum Number of SSH Retries Hit.  Did EC2 instance get configured with ssh correctly?')
                num_retries += 1 
                print('SSH failed, waiting 10 seconds...')
                time.sleep(10)
    
    # If we've reached this point, the instance is up and running.
    print('SSH passed')
    aws_system.install_all()


class AwsFab:
    
    def __init__(self, host_name, user, key_filename):
        '''Constructor for Class.  Sets up fabric environment.
        
        Args:
            host_name (string): ec2 public dns name
            user (string): ec2 username
            key_filename (string): file location for .pem file
        '''
        
        env.host_string = '{0}@{1}'.format(user, host_name)
        env.key_filename = [key_filename]
        print(key_filename)
        
    def test_cmd(self):
        '''A test command to see if everything is running ok.
        '''
        
        run('uname')    
    
    def install_all(self):
        '''Method to install all stuff on machine (except OneBusAway).
        '''
        
        self.install_git()
        self.install_maven()
        self.setup_pg()
    
    def install_git(self):
        '''Installs git.
        '''
        
        sudo('yum -y install git')
        
    def install_maven(self):
        '''Downloads and installs maven.
        '''
        
        # download and extract maven
        run('wget http://mirror.symnds.com/software/Apache/maven/maven-3/3.3.3/binaries/apache-maven-3.3.3-bin.tar.gz')
        sudo('tar xzf apache-maven-3.3.3-bin.tar.gz -C /usr/local')
        run('rm apache-maven-3.3.3-bin.tar.gz')
        with cd('/usr/local'):
            sudo('ln -s apache-maven-3.3.3 maven')
            
        # add maven to path
        run('export M2_HOME=/usr/local/maven')
        run('export M2=$M2_HOME/bin')
        run('export PATH=$M2:$PATH')
        run('source ~/.bashrc')
        
        # check that mvn command works
        run('mvn -version')
        
    def install_pg(self):
        '''Configures PostgreSQL for immediate use by OneBusAway.
        '''
        
        # install it
        sudo('yum -y install postgresql postgresql-server')
        
        # start server
        sudo('service postgresql initdb')
        
        # add login role
        
        # add group role
        
        # assign login role to group role
        
        # create db
        
        # give group privileges to db
        

def tear_down(instance_id=None, conn=None):
    '''Terminates a EC2 instance.
    
    Args:
        instance_id (string): The ec2 instance id to terminate.
        conn (boto.ec2.connection.EC2Connection): Connection to region.
    '''
    
    if not instance_id:
        instance_id = input('Enter instance id: ')
    
    if not conn:
        conn = get_aws_connection()
        
    print('Terminating instance')
    conn.terminate_instances([instance_id])
