Dookio: Your own PasS with Heroku-ish deployment of Docker containers
=====================================================================

As the description says, `Dookio` is a simple tool that allows you to deploy your own apps
by pushing to a remote server. The only requirement is to define a `Dockerfile` at the root level
with the building instructions.

> For scaling, listing and stopping app's containers, please have a look at [Dookio-cli](https://github.com/javidgon/dookio-cli)

The Stack consists in:
* [Hipache] (https://github.com/hipache/hipache)
* [Redis] (http://redis.io/) 
* [Gitreceive] (https://github.com/progrium/gitreceive)
* Two WSGI applications (server.py and node.py) (run by [Werkzeug] (http://werkzeug.pocoo.org/))
* [Docker] (https://www.docker.com/)

## 1. Quick Start

### 1.1 Single node installation (Linux - Ubuntu)

The quick start is automatized for "single node deployments" (this means that both the server, the app that receives your push, and the node, the app that creates your container, are the same machine). For more a more complex set up (multiple nodes spread in several machines), just go to the [next section] (https://github.com/javidgon/dookio#2-multiple-nodes-set-up).

The installation assumes that you are deploying it over a clean machine. If this is not the case, I'd recommend you to change the configuration. Also, the program sets some environment vars that can be modified if needed.

Having said that, there're at least three variables that you want to modify in any case:

```python
# In node/env.sh

# The linux user of the server machine e.g root
DOOKIO_SERVER_USER="root"
DOOKIO_SERVER_USER_PASSWORD="<linux_password>"

# In server/env.sh

# The domain that you want to use for connecting to your apps.
# e.g http://blabla.com
# In the end, your urls will look like e.g. http://app1.blabla.com
export DOOKIO_DOMAIN="blabla.com"
```

**Important**: In order to work, your domain "blabla.com" needs to point to the machine you are setting up, please have a look at the following link if you don't know how: [link](https://gist.github.com/ngoldman/7287753#3-configure-dns)

Well, after setting up the aforementioned environment vars, you just need to run the following scripts:

```python
# Run the following command for installing all the dependencies:

./single_node_bootstrap_linux.sh
```

```python
# Execute the following one for running hipache/redis and apps:

./single_node_run_linux.sh
```

### 1.2 General Use
As stated [here] (https://github.com/progrium/gitreceive#create-a-user-by-uploading-a-public-key-from-your-laptop), before the first use you need to run the following command in your laptop:

```python
$ cat ~/.ssh/id_rsa.pub | ssh <dookio_server_user>@<dookio_domain> "sudo gitreceive upload-key <username>"
```
Where `<username>` is by default `git` (for changing this user, just do `export GITUSER=<new_user>` in the server, and run `sudo gitreceive init` afterwards)

After that, you will be able to deploy your applications by doing, for example:

```bash
$ git remote add demo git@blabla.com:apache

$ git push demo master
Counting objects: 1, done.
Writing objects: 100% (1/1), 286 bytes | 0 bytes/s, done.
Total 1 (delta 0), reused 0 (delta 0)
----> Connecting with http://0.0.0.0:8000
----> Creating/updating the path git/apache
----> Compressing files...
Dockerfile
LICENSE
Makefile
README.md
run.sh
start.sh
supervisord-apache2.conf
----> Deploying app...
----> Processing information...
----> Setting up webserver rules...
----> Building docker container... (It might take a few minutes)
App successfully deployed! Go to http://apache.git.blabla.com
To git@blabla.com:apache
 + 61c180a...8c30e92 master -> master
```

## 2. "Multiple nodes" Set up
If you need to deploy many applications (or create a HA application) you probably want to have several nodes working for you. With `Dookio` this is straightforward.
First, modify the `NODES` file to include the IP Adresses of your nodes: E.g

````python
http://123.123.123.1
http://123.123.123.2
http://123.123.123.3
```

Second, in each node, follow the next steps:

* Install with `pip` the `node/requirements.txt` file (`pip install -r node/requirements.txt`)
* Export the `env vars` defined in the `node/env.sh` file (`source node/env.sh`)
* Run the `node/node.py` file (`python node/node.py`)

## 3. Contribute
Simply create a PR. Easy :)

## 4. TODO
* Be able to publish more ports in the containers (currently only the port 8000 is published in the container)
* Adapt `single_node_bootstrap.sh` to different platforms (MacOSX, ...)

## 5. Big thanks
[dotCloud] (https://www.dotcloud.com/) (creators of Hipache and Docker), [Redis community] (http://redis.io/) and [Jeff Lindsay] (http://progrium.com/blog/) (the creator of Gitreceive).

## 6. License
MIT
