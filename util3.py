import time, os, subprocess, math, datetime

import matplotlib.pyplot as plt
import matplotlib.dates
import pandas as pd

DEFAULT_OUTPUT_DIRPATH = 'static'

# Use of dpi with matplotlib is discussed here:
# https://stackoverflow.com/questions/13714454/specifying-and-saving-a-figure-with-exact-size-in-pixels
DPI = 100

OS_PID = os.getpid()
OS_TIME0 = time.time()

STATE_ABBREV = {
'AL': 'Alabama',
'AK': 'Alaska',
'AS': 'American Samoa',
'AZ': 'Arizona',
'AR': 'Arkansas',
'CA': 'California',
'CO': 'Colorado',
'CT': 'Connecticut',
'DE': 'Delaware',
'DC': 'District of Columbia',
'FL': 'Florida',
'GA': 'Georgia',
'GU': 'Guam',
'HI': 'Hawaii',
'ID': 'Idaho',
'IL': 'Illinois',
'IN': 'Indiana',
'IA': 'Iowa',
'KS': 'Kansas',
'KY': 'Kentucky',
'LA': 'Louisiana',
'ME': 'Maine',
'MD': 'Maryland',
'MA': 'Massachusetts',
'MI': 'Michigan',
'MN': 'Minnesota',
'MS': 'Mississippi',
'MO': 'Missouri',
'MT': 'Montana',
'NE': 'Nebraska',
'NV': 'Nevada',
'NH': 'New Hampshire',
'NJ': 'New Jersey',
'NM': 'New Mexico',
'NY': 'New York',
'NC': 'North Carolina',
'ND': 'North Dakota',
'MP': 'Northern Mariana Islands',
'OH': 'Ohio',
'OK': 'Oklahoma',
'OR': 'Oregon',
'PA': 'Pennsylvania',
'PR': 'Puerto Rico',
'RI': 'Rhode Island',
'SC': 'South Carolina',
'SD': 'South Dakota',
'TN': 'Tennessee',
'TX': 'Texas',
'UT': 'Utah',
'VT': 'Vermont',
'VI': 'Virgin Islands',
'VA': 'Virginia',
'WA': 'Washington',
'WV': 'West Virginia',
'WI': 'Wisconsin',
'WY': 'Wyoming',
}

def texify( s, printdict={} ):
    parts = printdict.get(s,s).rsplit('_',1)
    parts = [ parts[0].lower().replace('_','.'), ] + parts[1:]
    if parts[1:]:
        s = '%s $^{%s}$' % tuple(parts)
    return s

def report_date():
    return datetime.datetime.now().strftime( 'Reported %d%b%y %H:%M %p' )

def save( prefix='fig', output_dirpath=DEFAULT_OUTPUT_DIRPATH ):
    filename = '%s_%s.png' % ( prefix.lower(), ('%14.3f' % time.time()).replace('.','') )
    pathname = os.path.join( output_dirpath, filename )
    plt.savefig( pathname, dpi=DPI )
    subprocess.call([ "open", pathname ])
    return pathname

def log( *s ):
    print ( '(%8.2f) {%-5d} %s' % ( time.time()-OS_TIME0, OS_PID, ' '.join(map(str,s)) ) )

def is_null_val( val ):
    if isinstance( val, float ):
        return math.isnan( val )
    else:
        return pd.isnull( val )

def is_empty_series( s ):
    return len( s.dropna() )==0

class Plot:
    def __init__( self, plot_bases=None, tick_days=2, same_ymax=False, filename_prefix='fig', tidy_plot=True, ncols=None, pathname=None ):
        self.plot_bases = plot_bases or ()
        self.tick_days = tick_days
        self.same_ymax = same_ymax
        self.tidy_plot = tidy_plot
        self.n_plots = len( self.plot_bases ) or 1
        self.ncols = min( 2, self.n_plots ) if ncols is None else ncols
        self.axlist = []
        filename = '%s_%s.png' % ( filename_prefix.lower(), str(time.time()).replace('.','') )
        self.pathname = pathname or os.path.join( DEFAULT_OUTPUT_DIRPATH, filename )
        if not os.path.isdir( os.path.dirname( self.pathname ) ): 
            raise Exception('No directory to create output file: ' + os.path.abspath(self.pathname))

    def __enter__( self ):
        self.nrows = int( .6 + self.n_plots / float(self.ncols) )
        self.fig, _ = plt.subplots( self.nrows, self.ncols )
        self.fig.set_size_inches( 8*self.ncols, 5*self.nrows )
        return self

    def __exit__( self, type, value, tb ):
        if tb:
            raise
        else:
            if self.same_ymax:
                ymax = max([ ax.get_ylim()[1] for ax in self.axlist ])
                for ax in self.axlist:
                    ax.set_ylim([ ax.get_ylim()[0], ymax ])
            if self.tidy_plot:
                for ax in self.axlist:
                    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%d%b'))
                    #print 848484
                    # For counties with lots of missing data, and no data is plotted,
                    # setting the tick locator causes a fatal error.  For whatever reason
                    # the xlim span of these null-graphs is 81K.  So we eliminate that by
                    # ensuring that we have a reasonable scale for the x-axis. 
                    if ax.get_xlim()[1]-ax.get_xlim()[0] < 1000:
                        ax.xaxis.set_major_locator(plt.MultipleLocator( self.tick_days ))
                #for i in range( len(self.axlist), self.ncols*self.nrows ):
                #    print __file__, 'nono', i
                # See: https://stackoverflow.com/questions/10998621/rotate-axis-text-in-python-matplotlib
                #plt.xticks(rotation=45, horizontalalignment='right')
            self._save()

    def _save( self ):
        plt.savefig( self.pathname )

    #     def make_axlist( self ):
    #         self.axlist = [ plt.subplot( self.nrows, self.ncols, i+1 ) for i in range( self.nrows*self.ncols ) ]
    #         for ax in self.axlist:
    #             ax.js_labelleds = []
    #             ax.js_has_t_graph = False
    #         return self.axlist

    def subplot_axis( self, i ):
        # Expects < i > to be zero-based.  Matplotlib needs it to be 1-based.
        ax = plt.subplot( self.nrows, self.ncols, i+1 )   # like plt.subplot(...)
        ax.js_labelleds = []
        ax.js_has_t_graph = False
        self.axlist.append( ax )
        return ax

    #     def add_unpositioned_axis( self,*_ ):
    #         # Expects < i > to be zero-based.  Matplotlib needs it to be 1-based.
    #         ax = self.fig.add_axes()
    #         ax.js_labelleds = []
    #         ax.js_has_t_graph = False
    #         self.axlist.append( ax )
    #         return ax

    def enumerate( self ):
        for i, thing in enumerate( self.plot_bases ):
            yield i, self.subplot_axis(i), thing
    
    def tidy_ax( self, ax, yscale=None, grid=False, sensible_bottom=False, title=None, ylabel=None ):
        self.tidy_plot = ax.js_has_t_graph   # Turns off tick-formatting if no time series graphed
        ax.grid( bool( grid ) )
        if yscale:
            ax.set_yscale( yscale )
        if title:
            ax.set_title( title )
        if sensible_bottom:
            if not yscale: raise Exception('Must specify yscale if specifying tidy_bottom.')
            bottom = 0 if yscale=='linear' else 1
            ylim = ax.get_ylim()
            #ax.set_ylim([ max(bottom,ylim[0]), ylim[1] ])
            ax.set_ylim([ bottom, ylim[1] ])
        if ylabel:
            ax.set_ylabel( ylabel )

class BoundPDF:
    """
    Takes multiple .png files and joins them into a single .pdf file.
    Use < add1 > and < add2 > to accumulate .png files.
    Follows a two-step process:
    - Imagemagick converts individual .png files to .pdf.
    - PDFTK (PDF Toolkit) joins the individual .pdf files into one larger .pdf file.
    Input file can actually be any type of file that Imagemagick will convert to .pdf.
    The output file's name is derived from a supplied prefix and a time stamp.
    The time stamp is altered so more-recently-generated files are alphabetically first.
    Input files will be renamed to adopt time stamp and sequence number.
    """
    file_extension = '.pdf'

    def __init__( self, file_prefix, output_dirpath=None ):
        self.pathnames = []
        self.time_str = ( '%12.2f' % (2586637003 - time.time()) ).replace('.','')
        self.output_filename = '%s%s%s' % ( file_prefix, self.time_str, self.file_extension )
        self.output_pathname = self.output_filename if output_dirpath is None \
                               else os.path.join( output_dirpath, self.output_filename )
    
    def __enter__( self ):
        return self
    
    def add1( self, pathname ):
        self.pathnames.append( pathname )
    def add2( self, pathnames ):
        self.pathnames += pathnames
    
    def __exit__( self, type, value, tb ):
        """Am not sure this is the right way to handle errors.  Works well enough."""
        if tb:
            raise    # re-raises last error
        else:
            self.normal_exit()
    
    def normal_exit( self ):
        pdf_pathnames = []
        for i, pathname in enumerate( self.pathnames ):
            # Construct pathname for the .pdf file for this .png-file
            # Pathname will be in same directory as the original .png-file
            # Pathname will include time stamp and a sequence number for the .png-file
            dirpath = os.path.split( pathname )[0]
            filename_img = '%s_%02d%s' % ( self.time_str, i, os.path.splitext(pathname)[1] ) # splitext includes dot
            filename_pdf = os.path.splitext( filename_img )[0] + '.pdf'
            pathname_img = os.path.join( dirpath, filename_img )
            pathname_pdf = os.path.join( dirpath, filename_pdf )
            # Change original .png pathname to one that includes timestamp.
            os.rename( pathname, pathname_img )
            # Use the "convert" command (part of ImageMagick) to build the pdf
            command_list = ['convert', pathname_img, pathname_pdf ]
            print 'Converting to PDF:', command_list
            subprocess.call(command_list, cwd=os.getcwd())
            pdf_pathnames.append( pathname_pdf )
        command_list = ['pdftk',] + pdf_pathnames + [ 'output', self.output_pathname ]
        print 'Joining into PDF:', command_list
        subprocess.call(command_list, cwd=os.getcwd())
        subprocess.call( ['open', self.output_pathname], cwd=os.getcwd())

class PngMash( BoundPDF ):
    """
    This class really shouldn't exist, because it essentially does what the < Plot > class
    is supposed to do.  However, there were unresolvable problems with Plot when applied 
    to multiple doubling-times graphs, and this was a quicker way out than fighting
    Matplotlib internals.
    """
    file_extension = '.png'
    
    def normal_exit( self ):
        from PIL import Image
        images = [ Image.open( path ) for path in self.pathnames ]
        y9 = sum([ im.size[1] for im in images ])
        x9 = max([ im.size[0] for im in images ])
        master_im = Image.new(mode = "RGB", size = (x9, y9) )
        y0 = 0
        x0 = 0
        for im in images:
            x, y = im.size
            master_im.paste( im, ( x0, y0 ) ) #, x0+x, y0+x
            y0 += im.size[1]
        master_im.save( self.output_filename )
        subprocess.call( ['open', self.output_filename], cwd=os.getcwd())
