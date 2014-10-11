Dookio: Heroku-ish deployment of Docker containers
==================================================

As the description says, `Dookio` is a simple tool that allows you to deploy Docker containers
by pushing to a remote server.

The Stack consists in:
* [Hipache] (https://github.com/hipache/hipache)
* [Redis] (http://redis.io/) 
* [Gitreceive] (https://github.com/progrium/gitreceive)
* Two WSGI applications (server.py and node.py) (run by [Werkzeug] (http://werkzeug.pocoo.org/))
* [Docker] (https://www.docker.com/)

## Installation (Linux - Ubuntu)
The installation is automatized for "single node deployments" (this means that both the server and node are the same machine), but it should be straightforward to use a more complex set up.

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

Of course, in order to work, your domain "blabla.com" needs to point to the machine you are setting up.

Well, after setting up the aforementioned environment vars, you just need to run the following scripts:

```python
# Run the following command for installing all the dependencies:

./single_node_bootstrap_linux.sh
```

```python
# Execute the following one for running hipache/redis and apps:

./single_node_run_linux.sh
```

## Use
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
App successfully deployed! You can now see it in http://apache.blabla.com!
To git@blabla.com:apache
 + 61c180a...8c30e92 master -> master
```

## Installation (Another OS)
Just install the different components one by one. Dookio has not a particular contraint regarding the OS, but it's possible that some libraries have. Just play around! 

## Contribute
Simply create a PR. Easy :)

## Big thanks
Dotcloud (creators of Hipache and Docker), Redis community and Jeff Lindsay (the creator of Gitreceive).
