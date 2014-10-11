#!/bin/bash

echo "------> Automatic 'single' node run..."
echo "------> 1) Running Redis..."
sudo service redis-server start
echo "------> 2) Running Hipache webserver..."
sudo start hipache
echo "------> 3) Running Dookio server"
source server/env.sh
python server/server.py &
echo "------> 4) Running Dookio node"
source node/env.sh
python node/node.py &

echo "*****************************************************************************************"
echo "------> Congrats, all the required services are running!"
echo "*****************************************************************************************"
