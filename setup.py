from setuptools import setup, find_packages
 
setup(
    name='oba_rvtd_deployer',
    packages=find_packages(),
    install_requires=[
        'requests>=2.5.3',
        'boto>=2.38',
        'fabric>=1.10.1',
        'transitfeed>=1.2.14'
    ],
    entry_points={
        'console_scripts': [
            # config scripts
            'clean_config=oba_rvtd_deployer.config:clean',
            'setup_config=oba_rvtd_deployer.config:setup_all',
            'setup_aws=oba_rvtd_deployer.config:setup_aws',
            'setup_gtfs=oba_rvtd_deployer.config:setup_gtfs',
            'setup_oba=oba_rvtd_deployer.config:setup_oba',
            
            # aws/oba installation
            'launch_new_ec2=oba_rvtd_deployer.aws:launch_new',
            'tear_down_ec2=oba_rvtd_deployer.aws:tear_down',
            
            # oba/gtfs activation
            'validate_gtfs=oba_rvtd_deployer.gtfs:validate_gtfs',
            'update_gtfs=oba_rvtd_deploy.gtfs:update',
            'start_oba=oba_rvtd_deploy.oba:start',
            'stop_oba=oba_rvtd_deploy.oba:stop'
            
            # one command new deployment
            'deploy_master=oba_rvtd_deploy:run_all'
        ]
    }
)
