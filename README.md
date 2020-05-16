CoronaCurves was designed to visualize geographically-specific trends of the covid-19 epidemic, based on publicly-available data. It was developed by a member of the US military for personal convenience. 

The software may be operated from the command line or via a web browser.


# Disclaimer

The software is offered "as is" with absolutely no claim by any party as to its accuracy, suitability, safety, correctness, or any other characteristic. Use it entirely at your own risk. If you are ill or are concerned about someone who seems to be ill, consult a physician.

# Instructions for Web Use

1. On the home page choose a parameter to visualize. Both Johns Hopkins (JHU) and the New York Times (NYT) provide information on the number of covid-19 deaths and the number of identified new cases.

2. Choose one or more geographical localities by checking the corresponding check box. The names of some geographical localities are links -- click on the link to show sub-localities that may be chosen.

3. Click the "Draw Plots" button to display the plots for each geographic locality.  You will get something like this:

4. For help on how to interpret the plots, click the `How to Read` link on the home page or on a plot page.

# Installation: Desktop

CoronaCurves is written in pure Python (including Matplotlib, Numpy, and Scipy), so although it has been tested only on Macintosh, it should work on any operating system that supports Python 2.7 including Windows and Linux.

First create a Python virtual environment:

    virtualenv coronacurves_venv

Then `cd` into the virtualenv and activate it:

    cd coronacurves_venv
    source bin/activate

Next download the source code from Github and put it in the `coronacurves_venv` director under whatever name you like (e.g. `coronacurves_src`).

Next install into the virtualenv those Python modules required by CoronaCurves:

    pip install -r coronacurves_src/requirements.txt

You're now ready to go, but you'll want to cd into the source directory:

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

Finally, `cd` to the software's directory (if necessary) and grab the latest version of the public epidemiological data.  

    python flask_main.py -g

The cron file above checks for new data every 16 minutes.

# Running the Software

Test your installation:

       cd /home/corona
       python flask_main.py --test

This will probably generate on the console a few warning messages -- ignore them.  On a Mac, an image will open.  If you are `ssh`ing via a terminal session you will see nothing.

To start serving from the background:

    nohup python flask_main.py -r &
    tail -F nohup.out


The `-r` command option runs the software as a server process.  On Linux, it will server on port 80.

CoronaCurves was developed on a Mac.  So, when run on a Mac as a server, it serves
on port 5035 (for no good reason).  On anything else, e.g. Ubuntu on a cloud machine, it serves on port 80.
To alter these preferences, change `DEFAULT_SERVER_PORT` and/or `IS_MAC`.

# Bugs

* X-axis limits should be the same for all axes in a given plot.  Was not an issue until
less-dense data from Covid Tracking Project was imported.
* It would be nice to have y-axis tick marks only at integers.