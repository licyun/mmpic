#!/bin/sh
NAME="Restart MMPIC"
if [ ! -n "$NAME" ];then
    echo "no arguments"
    exit;
fi
echo $NAME
ID=`ps -ef | grep "$NAME" | grep -v "$0" | grep -v "grep" | awk '{print $2}'`
echo $ID
for id in $ID
do
kill -9 $id
echo "kill $id"
done
uwsgi --ini uwsgi.ini
echo  "Restart Success"
rm -rf cache/*
echo "Clear Cache"
echo "##############################################"
echo "Done"

