This software was designed to visualize geographically-specific trends of the covid-19 epidemic, based on publicly-available data. It was developed in haste by a member of the US military for personal convenience. 

The software may be operated from the command line or via a web browser.


# Disclaimer

The software is offered "as is" with absolutely no claim by any party as to its accuracy, suitability, safety, correctness, or any other characteristic. 

Use it entirely at your own risk. If you are ill or are concerned about someone who seems to be ill, consult a physician.

# Instructions for Desktop Use

The software should run well on all modern personal computers.  Consult the `instructions.md` file for instructions on installation and operation.

Before deciding to install and operate the software on your computer, know that it is more than a little crappy in quality, often non-Pythonic, and not well documented.  In fact, the code includes large blocks of unneeded code that the author may or may not get around to removing some day.

# Instructions for Web Use

1. On the home page choose a parameter to visualize. Both Johns Hopkins (JHU) and the New York Times (NYT) provide information on the number of covid-19 deaths and the number of identified new cases.

2. Choose one or more geographical localities by checking the corresponding check box. The names of some geographical localities are links -- click on the link to show sub-localities that may be chosen.

3. Click the "Draw Plots" button to display the plots for each geographic locality.  You will get something like this:

4. For help on how to interpret the plots, click the `How to Read` link on the home page or on a plot page.

# Bugs

* X-axis limits should be the same for all axes in a given plot.  Was not an issue until
less-dense data from Covid Tracking Project was imported.
* It would be nice to have y-axis tick marks only at integers.
