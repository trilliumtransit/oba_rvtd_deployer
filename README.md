# OneBusAway-RVTD Deployer

Script(s) to deploy and manage OneBusAway on Amazon EC2 for Rogue Valley Transportation District (RVTD)

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

## EC2 setup

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
