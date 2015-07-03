#!/bin/bash
#
# xwiki        
#
# copied and modified from: http://raibledesigns.com/tomcat/boot-howto.html
# description: 	Start up the xWiki server.
# chkconfig: 345 20 80
# Source function library.
. /etc/init.d/functions


RETVAL=$?
XWIKI_HOME="/usr/local/xwiki"

start() {
  if [ -f $XWIKI_HOME/start_xwiki.sh ];
    then
  echo $"Starting xWiki"
	nohup $XWIKI_HOME/start_xwiki.sh -p 8081 > /dev/null &
  fi
}

stop() {
  if [ -f $XWIKI_HOME/stop_xwiki.sh ];
    then
   echo $"Stopping xWiki"
   $XWIKI_HOME/stop_xwiki.sh -p 8081
   fi
}

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
 	echo $"Usage: $0 {start|stop|restart}"
	exit 1
	;;
esac

exit $RETVAL