#!/bin/bash
# Enviromental vars. PLEASE CHANGE THEM ACCORDINGLY
GITUSER=git

echo "------> Automatic 'single' node setup..."

echo "------> 1) Installing/Setting up Redis..."
sudo add-apt-repository -y ppa:rwky/redis
sudo apt-get update
sudo apt-get install -y redis-server
echo "------> 2) Installing/Setting up Hipache webserver..."
sudo npm install hipache -g
sudo cp server/hipache/upstart.conf /etc/init/hipache.conf
sudo cp server/hipache/config.json /etc/hipache.json
echo "------> 3) Installing 'Server' virtualenv"
sudo apt-get install -y python-dev
pip install -r server/requirements.txt
echo "------> 4) Installing 'Node' virtualenv"
pip install -r node/requirements.txt
echo "------> 5) Install progrium/gitreceive in $PATH"
# Install https://github.com/progrium/gitreceive in a $PATH location
wget https://raw.githubusercontent.com/progrium/gitreceive/master/gitreceive -P /usr/local/sbin/
# Create the user folder in which the apps will be stored
echo "------> 6) Creating $GITUSER user..."
sudo gitreceive init
echo "------> 7) Adapting the git receiver..."
# Use customized "receive" file.
cp server/receiver /home/$GITUSER/

echo "*****************************************************************************************"
echo "------> Congrats, the basic setup is completed. Please run the following command in a laptop as it's stated here: https://github.com/progrium/gitreceive#create-a-user-by-uploading-a-public-key-from-your-laptop"
echo "/////////////////////////////////////////////////////////////////////////////////////////"
echo "$ cat ~/.ssh/id_rsa.pub | ssh <gituser>@yourserver.com 'sudo gitreceive upload-key <username>'"
echo "/////////////////////////////////////////////////////////////////////////////////////////"
echo "------> After that you can just add 'dookio' as remote in your git repo: e.g 'git remote add dookio <gituser>@yourserver.com:<repo_name>'"
echo "------> And push to your new repo: e.g 'git push dookio master'"
echo "*****************************************************************************************"
