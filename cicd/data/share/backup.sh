#!/bin/bash

dirname=/data/backup/"code-`date +%Y%m%d%H%M`"
mkdir -p $dirname
cp -ar /data/code/* $dirname
rm -f /data/backup/last-version
ln -s $dirname /data/backup/last-version 


