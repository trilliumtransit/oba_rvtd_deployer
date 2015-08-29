#!/bin/bash
#
# downloads the latest static gtfs file
# then makes OBA build a bundle using that file

wget -O {gtfs_dl_file} {gtfs_static_url} -o {gtfs_dl_logfile}
cd {federation_builder_folder} && java -classpath .:target/* org.onebusaway.transit_data_federation.bundle.FederatedTransitDataBundleCreatorMain {gtfs_dl_file} {bundle_dir}
/home/{user}/tomcat/bin/shutdown.sh
/home/{user}/tomcat/bin/startup.sh