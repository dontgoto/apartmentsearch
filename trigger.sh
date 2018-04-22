#!/bin/bash
eval "export $(egrep -z DBUS_SESSION_BUS_ADDRESS /proc/$(pgrep -u $LOGNAME plasma)/environ)";
cd /home/fongo/sync/git/apartmentsearch/
/usr/bin/python3 /home/fongo/sync/git/apartmentsearch/newBot.py
