#!/bin/sh

# pass -v to the script to enable debug mode logging
python yate_proxy.py $* -dminecraft -s127.0.0.1:25565 -uYATEBot
