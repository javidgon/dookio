Dookio: Heroku-ish deployment of Docker containers
==================================================

As the description says, `dookio` is a simple tool that allows you to deploy Docker containers
by simply pushing to a remote server.

The Stack consists in:
* Hipache (as webserver)
* Redis (as db)
* Gitreceive (for triggering actions)
* Python (server and nodes apps)
* Docker (creation of containers)

## Installation (Linux - Ubuntu)
The installation is automatized for "single node deployments" (this means that both the server and node are the same machine), but it should be straightforward to use a more complex set up.

The installation assumes that you are deploying it over a clean machine. If this is not the case, I'd recommend you to change the configuration. Also, the program sets some environment vars that can be modified if needed.

Simple run the following command for installing all the dependencies (have a look at the printed instructions):
```python
./single_node_bootstrap_linux.sh
```

And the following one for running the servers and apps:
```python
./single_node_run_linux.sh
```

## Using it
Just have a look at the instructions stated here: https://github.com/progrium/gitreceive#create-a-user-by-uploading-a-public-key-from-your-laptop, the pushing process works exactly the same (`sudo gitreceive init` was done in the first script). The magic occurs internally.

## Installation (Another OS)
Just install the different components one by one. Dookio has not a particular contraint regarding the OS, but it's possible that some libraries have. Just play around! 

## Contribute
Simply create a PR. Easy :)

## Thanks
Dotcloud (creators of Hipache and Docker), Redis community and Jeff Lindsay (the creator of Gitreceive).
