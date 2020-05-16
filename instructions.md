# Requirements

CoronaCurves is written in pure Python (including Matplotlib, Numpy, Scipy, and Flask), so although it has been tested only on Macintosh, it should work on any operating system that supports Python 2.7 including Windows and Linux.

Use of the `-y` option, described later, requires `imagemagick` and `pdftk` (the PDF Toolkit).

# Installation: Desktop

First create a Python virtual environment:

    virtualenv coronacurves_venv

Then `cd` into the virtualenv and activate it:

    cd coronacurves_venv
    source bin/activate

Next, download the source code from Github and put it in the `coronacurves_venv` directory as a subfolder named whatever you like (e.g. `coronacurves_src`).

Next install into the virtualenv those Python modules required by CoronaCurves:

    pip install -r coronacurves_src/requirements.txt

You're now ready to run the software, but you'll first want to cd into the source directory:

    cd coronacurves_src

# Installation: Unix Server in the Cloud

## Introduction

This is the simplest possible installation, but has significant drawbacks:
1. The software is served from the `root` account, which is risky.  Creating a separate
user account is recommended, but is left as an exercise for the reader.
2. The software is served by Flask only, not a more production-suited server such as Nginx.
3. Extra steps are needed to serve over HTTPS, vs. HTTP.

If you have the software on a desktop Mac and want to upload it to your cloud
machine, you can use `rsync`:

    rsync -avzr * root@AA.BBB.CC.DDDD:/home/corona/

Or course, you could also simply install from GitHub.

## Installation Procedure

Sign in to your cloud machine and do the following:

    apt-get update
    apt install python
    apt install python-pip

    cd /home/corona
    pip install -r requirements.txt

To have the software check for new data every 16 minutes, set up a `cron` job, as follows:

    # Can confirm cron is installed via: which cron
    # The "sudo" seems to be necessary when updating the crontab.
    systemctl enable cron
    sudo crontab -e
    [choose the "ed" option if offered — that’s what’s assumed below]
    $a
    */16 * * * * /home/corona/python flask_main.py -g
    .
    w
    q
    service cron start

# Running via Command Line

Assuming you have `cd`-ed into the directory having the CoronaCurves source code, you can see the command line options with:

    python flask_main.py -h

First, grab the latest version of the public epidemiological data using the `-g` option:

    python flask_main.py -g

 You can test your installation with:

    python flask_main.py --test

This will probably generate on the console a few warning messages -- ignore them.  On a Mac, an image will open.  If you are `ssh`ing via a terminal session you will see nothing.

## Options: `--pchan` and `--pgeo`

To plot a particular data channel, use the `--pchan` option.  To plot a particular geography (or geographies), use the `--pgeo` option.  Example:

    python flask_main.py --pgeo deaths_NYT --pgeo USA~Maryland~Baltimore

If there is a non-alphabetic character in the geography string, escape it or put the argument in quotes:

    python flask_main.py --pgeo deaths_NYT --pgeo "USA~Maryland~Anne Arundel"

You can specify multiple geographies by joining three-field geo-specification with an `@` character:

    python flask_main.py --pgeo deaths_NYT --pgeo USA~Maryland~Baltimore@Canada~Manitoba~

In summary, the syntax of the `--pgeo` option is:
 1. Each geographic specification has three fields, separated by a tilde (`~`), in the format NATION~STATE~COUNTY.  There are always two tildes, even if the fields are null.  Examples are: USA~~, USA~Iowa~, Bolivia~~, Canada~Manitoba~.
 2. Upper/lower-case matters.
 3. Multiple geographies may be specified by interposing an `@` character.  Example: Denmark~Greenland~@Sweden~~@USA~Maine~

## Options: `-y` and `--ypdf`

If you frequently generate the same plots, you can specify them as a `.yaml` file and tell the software to generate plots according to that file.  The output will be a `.pdf` document, not a `.png` image.

To do this you will need to have `imagemagick` and `pdftk` (the PDF Toolkit) installed on your machine -- this may not be possible for Windows.  See the `requirements.txt` file for comments pointing to resources that can help you with installation on Macintosh.

Example:

    python flask_main.py -y test.yaml --ypdf first_test

This will generate a `.pdf` file whose name starts with "first_test' and which contains the plots specified in the file named `test.yaml`.  All `.yaml` input files are in the directory `yaml-input` and all output goes into the directory `yaml-output`.

# Running as a Web Server

To start serving in the foreground:

    python flask_main.py -r

To start serving from the background:

    nohup python flask_main.py -r &
    tail -F nohup.out


CoronaCurves was developed on a Mac.  So, when run on a Mac as a server, it serves on port 5035 (for no good reason).  On anything else, e.g. Ubuntu on a cloud machine, it serves on port 80.  To alter these preferences, change `DEFAULT_SERVER_PORT` and/or `IS_MAC`.
