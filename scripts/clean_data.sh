#!/bin/bash

# Clean Redis.
redis-cli FLUSHDB

# Stop all the containers.
docker stop $(docker ps -a -q)

# Remove all the containers.
docker rm $(docker ps -a -q)

# Remove untagged images.
docker rmi $(docker images -q --filter "dangling=true")

# Kill node and server.
sudo pkill python

# Remove used ports file.
rm USED_PORTS
