#!/bin/bash

function start_profile(){
echo "start telegraf in dryrun mode"
source /cvmfs/softdrive.nl/apmechev/go_packages/init.sh 

echo "" > ${RUNDIR}/pipeline_step
mkfifo ${RUNDIR}/pipeline_fifo


#while /bin/true; do 
#   monitor_step
#done  &



########
#telegraf --config /cvmfs/softdrive.nl/apmechev/go_packages/src/github.com/influxdata/telegraf/telegraf.conf 2>/dev/null &
########
COLL_PID=$!
cd ${RUNDIR}

}


function stop_profile(){
echo "killing tcollector"
kill $COLL_PID
}

function monitor_step(){
 export PIPELINE_STEP=$( cat ${RUNDIR}/pipeline_step )
 
  if [ "$PIPELINE_STEP" != "$CURR_STEP"  ]; then
      if [ ! -z $( echo $COLL_PID ) ]; then
          kill $COLL_PID;
          killall telegraf;
      fi
      launch_telegraf &
      export COLL_PID=$!
      export CURR_STEP=$PIPELINE_STEP;
  fi; 
 sleep 1;
}

function monitor_loop(){
 while /bin/true; do
       monitor_step
 done  
}

function launch_telegraf(){
   telegraf --config /cvmfs/softdrive.nl/apmechev/go_packages/src/github.com/influxdata/telegraf/telegraf.conf 2>/dev/null 
}
