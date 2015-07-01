# OneBusAway-RVTD Deployer

Script(s) to deploy and manage OneBusAway on Amazon EC2 for Rogue Valley Transportation District (RVTD)

## Table of Contents

* [Installation](#installation)
* [EC2 Setup](#ec2-setup)
* [Config Files](#config-files)
    * [aws.ini](#awsini)
    * [gtfs.ini](#gtfsini)
    * [oba.ini](#obaini)
* [Running Scripts](#running-scripts)
* [Disabling IPv6](#disabling-ipv6)
* [PostgreSQL Setup](#ec2-postgresql-setup)

## Installation

The project is based of off python 2.7, but is best used with the `virtualenv` development scheme.

1. Install Python 2.7
2. Install virtualenv: `$ [sudo] pip install virtualenv`
3. Clone the github project: `$ git clone https://github.com/trilliumtransit/oba_rvtd_deployer.git`
4. Instantiate the virtual python environment for the project using python 2.7: 
  - Windows: `virtualenv --python=C:\Python27\python.exe oba_rvtd_deployer`
  - Linux: `virtualenv -p /path/to/python27 oba_rvtd_deployer`
5. Browse to project folder `cd oba_rvtd_deployer`
6. Activate the virtualenv: 
  - Windows: `.\Scripts\activate`
  - Linux: `bin/activate`
7. (Windows only) Manually install the `pycrypto` library.  The followin command assumes you have 32 bit python 2.7 installed: `pip install http://www.voidspace.org.uk/python/pycrypto-2.6.1/pycrypto-2.6.1-cp27-none-win32.whl`  If 64 bit python 2.7 is installed, run the following command instaed:  `pip install http://www.voidspace.org.uk/python/pycrypto-2.6.1/pycrypto-2.6.1-cp27-none-win_amd64.whl`
8. Install the python project using develop mode: `python setup.py develop`

## EC2 Setup

You will need to do the following for automatically launching Amazon EC2 instances using the scripts:

- Create AWS account
 - Get the access key
 - Get the secret access key
- Create security group
 - Add your IP to list of allowed inbound traffic [(see aws docs)](http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/authorizing-access-to-an-instance.html).
- Create key pair [(see aws docs)](http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html).
 - Download .pem file to computer
- (Windows only) instally PuTTY and PuTTYgen
 - [Download from here](http://www.chiark.greenend.org.uk/~sgtatham/putty/download.html).
 - Create .ppk file [(see aws docs)](http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/putty.html).

## Config Files

You'll need to create a bunch of config files before running the deployment scripts.  Run the script `setup_config` to be prompted for each setting, or create a new folder called `config` and add the files manually.  All config files are .ini files and have a single section called 'DEFAULT'.

### aws.ini

| Setting Name | Description |
| --- | --- |
| ami_id | The base ami to start from.  Defaults to `ami-3689325f` (Amazon Linux). |
| aws_access_key_id | Access key for account. |
| aws_secret_access_key | Secret access key for account. |
| delete_volumes_on_tear_down | When tearing down instance, also delete volumes.  If using CentOS, you should set this to `true`.  Defaults to `false`.
| key_filename | The filename of your .pem file. |
| key_name | The name of the secret key for the EC2 instance to use. |
| instance_name | The name to tag the instance with. |
| instance_type | The EC2 instance type.  [(See instance types)](http://aws.amazon.com/ec2/pricing/). |
| region | The AWS region to connect to. |
| security_groups | Security groups to grant to the instance.  If more than one, seperate with commas. |
| user | The user to login as when connecting via ssh.  Defaults to `ec2-user`. |
| volume_size | Size of the AWS Volume for the new instance in GB.  Defaults to `40`. | 

### gtfs.ini

| Setting Name | Description |
| --- | --- |
| gtfs_static_url | The url where the gtfs static file can be found. |
| gtfs_rt_trip_updates_url | The url for the gtfs-rt trip updates. |
| gtfs_rt_service_alerts_url | The url for the gtfs-rt service alerts. |
| gtfs_rt_vehicle_positions_url | The url for the gtfs-rt vehicle positions. |

### oba.ini

| Setting Name | Description |
| --- | --- |
| allow_api_test_key | Whether or not to set a test key for the api-webapp.  Set to `true` if desired. |
| oba_base_folder | OneBusAway based folder.  Defaults to `onebusaway-application-modules-rvtd`. |
| oba_git_branch | OneBusAway git branch to checkout.  Defaults to `rvtd-1.1.13.install`. |
| oba_git_repo | OneBusAway git repo to checkout from.  Defaults to `https://github.com/trilliumtransit/onebusaway-application-modules-rvtd.git`. |
| pg_username | The role that OneBusAway will use when connecting to postgresql. |
| pg_password | The password that OneBusAway will use when connecting to postgresql. |

## Running Scripts

If using linux, the executable files to run scripts will be in the `bin` folder instead of `Scripts`.  In the remainder of the docs, whenever it says "run script `script_name`", you'll run the script by doing `bin/script_name` or `.\Scripts\script_name` on linux and windows respectively.

| Script Name | Description |
| --- | --- |
| clean_config | Deletes the "config" folder. |
| setup_config | Helper script to create configuration files for AWS, OneBusAway and updating and validating GTFS. |
| launch_new_ec2 | Launches a new Amazon EC2 instance and installs the essential software to run OneBusAway. |
| tear_down_ec2 | Terminates an Amazon EC2 instance. |
| install_oba | Installs OneBusAway on server by compiling with maven. |
| validate_gtfs | Downloads and validates the static GTFS. |
| update_gtfs | Creates a new data bundle for OneBusAway. Validate the GTFS if no GTFS file found. |
| deploy_oba | Deploys the OneBusAway webapps to Tomcat. |
| start_oba | Starts Tomcat and xWiki Servers. |
| stop_oba | Stops Tomcat and xWiki Servers. |
| deploy_master | Combines following scripts in order: launch_new_ec2, install_oba, update_gtfs, deploy_oba, start_oba. |

## Disabling IPv6

Some webapps try to serve themselves using IPv6, so IPv6 is disabled on the machine.  This must be done manually.  Follow these steps to disable IPv6:

1.  `sudo su`
2.  `echo "net.ipv6.conf.default.disable_ipv6=1" >> /etc/sysctl.conf`
3.  `echo "net.ipv6.conf.all.disable_ipv6 = 1" >> /etc/sysctl.conf`
4.  `sysctl -p`

## EC2 PostgreSQL Setup

There is some manual setup required for setting up PostgreSQL.

0.  Change to root user:  `sudo su`.
1.  Edit the file `/var/lib/pgsql/data/pg_hba.conf`.  Change this line:
    ```
    local   all         all                                       peer
    ```

    to this:

    ```
    local   all         all                                       trust
    ```

2.  Start postgresql: `sudo service postgresql start`
3.  Enter into the psql edit mode:  `psql -U postgres`
3.  Create a login user for OneBusAway (replace username with your choice): `CREATE ROLE username1 PASSWORD 'password';`
4.  Create a group role for that user (replace group role name with your choice): `CREATE ROLE groupname1;`
5.  Grant group role to login user (replace names): `GRANT groupname1 TO username1;`
6.  Create the databases (KEEP db names!): `CREATE DATABASE org_onebusaway_users ENCODING = 'UTF8';` `CREATE DATABASE org_onebusaway_database ENCODING = 'UTF8';`
7.  Grant all on the databases to group role (replace group role name): `GRANT ALL ON DATABASE org_onebusaway_users TO groupname1;` `GRANT ALL ON DATABASE org_onebusaway_database TO groupname1;`
8.  Edit the file `/var/lib/pgsql/data/pg_hba.conf`.  Change these lines:
    ```
    local   all             all                                     trust
    # IPv4 local connections:
    host    all             all             127.0.0.1/32            ident
    ```

    to this:

    ```
    local   all             all                                     md5
    # IPv4 local connections:
    host    all             all             127.0.0.1/32            md5
    ```
9.  Restart postgresql: `sudo service postgresql restart`
