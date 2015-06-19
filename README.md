# OneBusAway-RVTD Deployer

Script(s) to deploy and manage OneBusAway on Amazon EC2 for Rogue Valley Transportation District (RVTD)

## Table of Contents

* [Installation](#installation)
* [Running Scripts](#running-scripts)
* [EC2 Setup](#ec2-setup)

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

## Running Scripts

If using linux, the executable files to run scripts will be in the `bin` folder instead of `Scripts`.  In the remainder of the docs, whenever it says "run script `script_name`", you'll run the script by doing `bin/script_name` or `.\Scripts\script_name` on linux and windows respectively.

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
| key_filename | The filename of your .pem file. |
| key_name | The name of the secret key for the EC2 instance to use. |
| instance_name | The name to tag the instance with. |
| instance_type | The EC2 instance type.  [(See instance types)](http://aws.amazon.com/ec2/pricing/). |
| region | The AWS region to connect to. |
| security_groups | Security groups to grant to the instance.  If more than one, seperate with commas. |
| user | The user to login as when connecting via ssh. |

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
| pg_username | The username that OneBusAway will use when connecting to postgresql. |
| pg_password | The password that OneBusAway will use when connecting to postgresql. |
