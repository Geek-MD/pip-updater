# pip-updater
Python script designed to update pip packages

## Previous steps

Clone this repo with...
  
```
git clone https://github.com/Geek-MD/pip-updater.git
```

Now execute the *start.sh* file with the following command. This will install all dependencies needed by the script
listed on *requirements.txt*.

```
./start.sh
```

Once the script is finished, you will get help information on how to run the python script.

## Basic configuration

The basic syntax to run the script is as the following examples.

```
python3 pip-updater.py
```

You can check the script help by using *-h* or *--help* option.

```
python3 pip-updater.py -h
python3 pip-updater.py --help
```

You can check the script version by using *-v* or *--version* option.

```
python3 pip-updater.py -v
python3 pip-updater.py --version
```

## Optional modificators

There are 3 optional modificators.

With *-l* or *--list* you can just list all outdated pip packages, without updating them. This option is 

With *-i* or *--interactive* you will be prompted to answer for each package if it will be updated or not.

Finally with *-e* or *--exceptions*, the script will search in exceptions.txt, for packages which you don't want to be updated, or packages you want to be freezed at a specific version. Write one package per line, using "name" format if you want to exclude it from updating, or using "name==version" format if you want to freeze a package at a specific version.

*--interactive* and *--exceptions* options can be used together, but *--list* excludes the other options.

Here's an example of how *exceptions.txt* will look like. In this example, argparse will be freezed at 3.11 and numpy will not be updated.

```
argparse==3.11
numpy
```
