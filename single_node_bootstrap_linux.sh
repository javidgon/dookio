#!/bin/bash
# Enviromental vars. PLEASE CHANGE THEM ACCORDINGLY
GITUSER=git

echo "------> Automatic 'single' node setup..."

echo "------> 1) Installing/Setting up Redis..."
sudo add-apt-repository -y ppa:rwky/redis
sudo apt-get update
sudo apt-get install -y redis-server
echo "------> 2) Installing/Setting up Hipache webserver..."
sudo apt-get install -y npm
sudo npm install hipache -g
sudo cp server/hipache/upstart.conf /etc/init/hipache.conf
sudo cp server/hipache/config.json /etc/hipache.json
echo "------> 3) Installing/Setting up Docker..."
wget -qO- https://get.docker.io/gpg | sudo apt-key add -
sudo sh -c "echo deb http://get.docker.io/ubuntu docker main > /etc/apt/sources.list.d/docker.list"
sudo apt-get update
sudo apt-get install lxc-docker
echo "------> 4) Installing 'Server' requirements"
sudo apt-get install -y python-dev python-setuptools
easy_install pip
pip install -r server/requirements.txt
echo "------> 5) Installing 'Node' requirements"
pip install -r node/requirements.txt
echo "------> 6) Install progrium/gitreceive in $PATH"
# Install https://github.com/progrium/gitreceive in a $PATH location
if [ ! -f /usr/local/sbin/gitreceive ]; then
	wget https://raw.githubusercontent.com/progrium/gitreceive/master/gitreceive -P /usr/local/sbin/
	sudo chmod +x /usr/local/sbin/gitreceive
fi
# Create the user folder in which the apps will be stored
echo "------> 7) Creating $GITUSER user..."
sudo gitreceive init
echo "------> 8) Adapting the git receiver..."
# Use customized "receive" file.
cp server/receiver /home/$GITUSER/

echo "*****************************************************************************************"
echo "------> Congrats, the bootstrap setup is completed. Please follow the rest of the"
echo "        instructions from the README file. "
echo "*****************************************************************************************"
