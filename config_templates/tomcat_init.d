#!/bin/bash
#
# tomcat        
#
# copied and modified from: http://raibledesigns.com/tomcat/boot-howto.html
# description: 	Start up the Tomcat servlet engine.
# chkconfig: 345 20 80
# Source function library.
. /etc/init.d/functions


RETVAL=$?
CATALINA_HOME="/home/{user}/tomcat"

start() {{
  if [ -f $CATALINA_HOME/bin/startup.sh ];
    then
  echo $"Starting Tomcat"
	$CATALINA_HOME/bin/startup.sh
  fi
}}

stop() {{
  if [ -f $CATALINA_HOME/bin/shutdown.sh ];
    then
   echo $"Stopping Tomcat"
   $CATALINA_HOME/bin/shutdown.sh
   fi
}}

case "$1" in
 start)
        start
	;;
 stop)
        stop
 	;;
 restart)
		stop
		start
	;;
 *)
 	echo $"Usage: $0 {{start|stop|restart}}"
	exit 1
	;;
esac

exit $RETVAL