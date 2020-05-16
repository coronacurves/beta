"""
3.7 - Moved back to desktop. Plots always include both colors.
3.6 - Cloned from coronacurves3.5.  Runs multithreaded: new processes call Matplotlib.

CRON JOBS
---------
Here is a nice trick for debugging cron jobs.
It is very helpful to direct output from the job to the terminal (stdout).
To do this, give this unix command:
    tty
In the crontab file, direct output of the cronjob to that result, e.g.:
    */10 * * * * sudo python /home/corona/flask_main.py -g > /dev/pts/0
"""

import os, md5, subprocess, sys, collections
IS_MAC = ( sys.platform=='darwin' )

# Not used in this file, but simplifies import in later modules
import matplotlib
matplotlib.use('Agg')                       # Cannot be TkAgg to run in web server

import jinja2
import flask
app = flask.Flask( __name__ )

import web_grab
import web_graphline
import web_stacker as stacker
import util3                # After other imports so Matplotlib backend loaded already

__VERSION__ = '3.7'

LEFT_TIME = 45              # Plots will look back 45 days. Could be parameter someday.

DEFAULT_SERVER_PORT = 5035 if IS_MAC else 80
JINJA_ENV = jinja2.Environment( loader=jinja2.FileSystemLoader( "templates" ) )

# A few web and Flask-related parameters that are really constants.
HOME_HREF = '/'         # Of course, but helpful to define as constant
HOW_TO_READ_HREF = "/how-to-read.html"
YAML_INPUT_DIRPATH = 'yaml-input'
YAML_OUTPUT_DIRPATH = 'yaml-output'
STATIC_HREF0   = '/static'
STATIC_DIRPATH = 'static'

# These constants are used in HTML/Javascript
SEP = '~'
SERIES_NAME_PARM = 'series_name'

# These are essential parameters that many Jinja templates will need.
BASE = {
        'SYSNAME': 'CoronaCurves',
        'HOME_HREF': HOME_HREF,
        'HOW_TO_READ_HREF': HOW_TO_READ_HREF,
        'BUTTON_TEXT': "Draw Plots",
}
def base( dikt ):
    dikt.update( BASE )
    return dikt

############################################################################################
############################################################################################
# URL Mappings
############################################################################################
############################################################################################

@app.route( HOME_HREF )
def home():
    sources_and_series = collections.defaultdict( list )
    for series in web_grab.Series.AlphaList():
        for source in series.source_instances:
            if series not in sources_and_series[ source.full_source_sortnum_and_name ]:
                sources_and_series[ source.full_source_sortnum_and_name ].append( series )
    #print 8424, sources_and_series
    #print 9242, sorted( sources_and_series.items(), key=lambda abz: abz[0][0] )
    return JINJA_ENV.get_template( "home.html" ).render(base({ 
        'SOURCES_AND_SERIES': sorted( sources_and_series.items(), key=lambda abz: abz[0][0] ),
        'SERIES_LIST': web_grab.Series.AlphaList(),
        'SEP': SEP,
        'SERIES_NAME_PARM': SERIES_NAME_PARM,
        }))

@app.route( HOW_TO_READ_HREF )
def how_to_read():
    return JINJA_ENV.get_template( "how-to-read.html" ).render(base({ 
        }))

@app.route("/bookmarks.html")
def bookmarks(): return JINJA_ENV.get_template( "bookmarks.html" ).render(base({}))

@app.route("/about.html")
def about(): return JINJA_ENV.get_template( "about.html" ).render(base({}))

@app.route("/rabidbatbitesbear")
def grab_web_data():
    all_ok = web_grab.check_for_new_web_sources()
    return '<html><body>%s. <a href="%s">Home</a></body></html>' % ("OK" if all_ok else "Error", HOME_HREF)

@app.route("/make_plots")
def make_plots():
    # Extract parameters from a web request and then call plotting routine.
    # The specification for the plot is given by ?/& arguments in the URL.
    # Note that this scheme omits the date.
    # Did it this way so that a page may be bookmarked once and then revisited
    # daily, each time providing the plot for the last set of data.
    
    # Extract < series_name > parameter from request-args, e.g. cases_NYT
    series_name = flask.request.args.get( SERIES_NAME_PARM )

    # Extract geo-specs from request-args, e.g. [['Brazil','',''],['USA','California','Fresno','']]
    # Uses < series_name > as a filter to decide which checkboxes to heed.
    geo_specs = [ tuple( key.split(SEP)[1:] )
                  for key in flask.request.args.keys() 
                  if (key != SERIES_NAME_PARM) and key.startswith( series_name ) ]

    if not geo_specs:
        return JINJA_ENV.get_template( "empty-message.html" ).render(base({}))

    geo_specs.sort()
    return plot( None, series_name, geo_specs )

def plot( pathname, series_name, geo_specs ):
    # Generate the filename of the image's path.
    # The filename has to encapsulate all parameters needed to draw the plot, other
    # than the version of the series that is being used (that is in directory-name).
    # For now, this means only the geo-specs.  Someday may include < left_time >.
    m = md5.new()
    m.update( series_name + '/'.join([','.join(geospec) for geospec in geo_specs]) )
    filename = m.hexdigest() + '.png'

    # Generate the directory name of the image's path on disk (and URL).
    series = web_grab.Series.GetSeries( series_name )
    series_version = series.timedname( compact=True )
    output_dirpath = os.path.join( STATIC_DIRPATH, series_version )
    if not os.path.isdir( output_dirpath ):
        os.makedirs( output_dirpath )

    figure_href = os.path.join( STATIC_HREF0, series_version, filename )
    pathname = os.path.join( output_dirpath, filename )

    # Build the image only if it doesn't already exist on disk.
    if not os.path.isfile( pathname ):
        #build_image( series_name, geo_specs, pathname )
        script = os.path.abspath( __file__ )
        #pathname = os.path.abspath( pathname )
        call = [ 'python', script, '-b', encode_places( pathname, series_name, geo_specs ) ]
        subprocess.call( call )

    return JINJA_ENV.get_template( "plot_host.html" ).render(base({ 
        'PARMNAME': series_name,
        'FIGURE_HREF': figure_href,
        'GEO_NAMES': [ ', '.join( filter(None,geo_spec)[::-1] ) 
                       for geo_spec in geo_specs ]
        }))

# Entry point for -b command
def build_image( pathname, series_name, geo_specs, open_plot=False ):
    # Writes plot file to disk.  Returns pathname for the plot file.  
    # Returned pathname will be < pathname > if supplied, else concocted from time.
    print 'Building image for', encode_places( pathname, series_name, geo_specs )
    series = web_grab.Series.GetSeries( series_name )
    sergeos = [ web_graphline.SerGeo( filter( None, geo_spec )[-1],   # geo name
                                      series.get_df( geo_spec ),      # pandas dataframe
                                      series_name,
                                      LEFT_TIME )
                for geo_spec in geo_specs ]
    dataset_when = series.timedname( alpha=True )
    fig_rel_path = stacker.stackerX( sergeos, series_name, dataset_when, pathname )
    print 'Wrote plot to', fig_rel_path
    if open_plot:
        subprocess.call( ['open', fig_rel_path ] )
    return fig_rel_path

############################################################################################

# Example: 'xyz.png@cases_NYT@USA~New Hampshire~@USA~New Hampshire~Grafton@USA~Texas~Bexar@USA~Louisiana~'
PLACE_SEP1 = '~'
PLACE_SEP2 = '@'
def encode_places( pathname, parameter_name, tuples ):
    return PLACE_SEP2.join([ pathname, 
                             parameter_name, 
                             PLACE_SEP2.join([ PLACE_SEP1.join(s3) for s3 in tuples ]) ])
def decode_places( s ):
    pathname, parameter_name, s2 = s.split( PLACE_SEP2, 2 )
    return pathname, parameter_name, [ s3.split( PLACE_SEP1 ) for s3 in s2.split( PLACE_SEP2 ) ]

def decode_yaml( filename ):
    import yaml
    with open( os.path.join( YAML_INPUT_DIRPATH, filename ), 'r' ) as f:
        channel_dicts = yaml.load( f )
    answer = []
    for channel_dict in channel_dicts:
        for channel, sublist in channel_dict.items():
            geo_strings = _decode1( [], [], sublist )
        answer.append( [channel, geo_strings] )
    return answer

def _decode1( geo_strings, prefixes, subitem ):
    if subitem:
        if isinstance( subitem, list ):
            for elt in subitem:
                geo_strings = _decode1( geo_strings, prefixes, elt )
        elif isinstance( subitem, dict ):
            for geo, substuff in subitem.items():
                geo_strings = _decode1( geo_strings, prefixes + [geo,], substuff )
        elif isinstance( subitem, basestring ):
            new_guy = prefixes + [subitem,]
            while len(new_guy)<3: new_guy.append('')
            geo_strings.append( PLACE_SEP1.join( new_guy ) )
        else:
            raise Exception( 'Unanticipated item in YAML: %s' % subitem )
    return geo_strings
 
def title_page( main_title, yaml_filename ):
    # Pillow barfs with some images created by Gimp.
    # https://github.com/python-pillow/Pillow/issues/3287
    # Had to convert Gimp .png to .tiff (in Gimp), then ImageMagick convert .tiff to .png.
    import datetime
    with util3.Plot(tidy_plot=False) as plot:
        ax = plot.subplot_axis(0)
        ax.set_xlim([0,100])
        ax.set_ylim([0,100])
        mid = 50
        ax.set_xticks([])
        ax.set_yticks([])
        today = datetime.date.today().strftime('%d %b %Y')
        ax.text( mid, 95, main_title, fontsize=32, ha='center', va='top' )
        ax.text( mid, 82, 'Based on: ' + yaml_filename, fontsize=14, ha='center', va='top' )
        ax.text( mid, 55, today, fontsize=24, ha='center', va='bottom' )
        ax.text( mid, 35, 'No restrictions on disclosure', fontsize=14, ha='center', va='bottom' )
        ax.text( mid,  2, 'github.com/coronacurves/beta', fontsize=10, ha='center', va='bottom' )
        return plot.pathname

############################################################################################
############################################################################################
# Main
############################################################################################
############################################################################################

DEFAULT_P = '@cases_NYT@USA~New Hampshire~@USA~New Hampshire~Grafton@USA~Texas~Harris@USA~Louisiana~'

def main( args ):
   
    if args.g:
        # Must precede -r so we can say -gr
        print 'Will grab data from web'
        web_grab.check_for_new_web_sources()

    if args.test:
        build_image( *decode_places( DEFAULT_P ), open_plot=True )

    if args.pgeo:
        build_image( *decode_places( PLACE_SEP2 + args.pchan + PLACE_SEP2 + args.pgeo ), open_plot=True )

    if args.y:
        paths = []
        if args.ypdf: paths.append( title_page( 'Covid-19 Pandemic Trends', args.y ) )
        for channel, geo_strings in decode_yaml( args.y ):
            paths.append( build_image( *decode_places( PLACE_SEP2 + channel + PLACE_SEP2 + PLACE_SEP2.join(geo_strings) ), open_plot=True ))
        if args.ypdf:
            with util3.BoundPDF( args.ypdf, output_dirpath=YAML_OUTPUT_DIRPATH ) as pdf:
                pdf.add2( paths )

    if args.b:
        build_image( *decode_places( args.b ), open_plot=False )

    if args.q:
        # This will always build a new image, and it will be in main output directory.
        #fig_rel_path = build_image( '', 'cases_NYT', [('USA','New Hampshire',''), ('USA','New Hampshire','Grafton'), ('USA','Texas','Bexar'), ('USA','Louisiana','' )] )
        build_image( '', 'cases_JHU', [('USA','Texas','Bexar'), ], open_plot=True )
    
    if args.r:
        print 'Will run on port', DEFAULT_SERVER_PORT
        if IS_MAC:
            app.run( port=DEFAULT_SERVER_PORT)
        else:
            app.run( host='0.0.0.0', port=DEFAULT_SERVER_PORT)
 
    print 'Done.'
    
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", action="store_true", help="run as web server")
    parser.add_argument("-g", action="store_true", help="grab data from web")
    parser.add_argument("-b", help="build plot")
    parser.add_argument("-q", action="store_true", help="experiment du jour [DEV]")
    parser.add_argument("--pchan", help="plot this data-channel-name", default="cases_JHU")
    parser.add_argument("--pgeo",  help="plot this geography-string. Fmt=%s" % PLACE_SEP1.join(['X','Y','Z']) )
    parser.add_argument("-y",      help="name of yaml file-path to plot")
    parser.add_argument("--ypdf",  help="Bind -y output into PDF with this name")
    parser.add_argument("--test", action="store_true", help="test plot")
    args = parser.parse_args()
    main( args )
