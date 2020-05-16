# !/usr/bin/python

import StringIO, md5, os, time, datetime, glob, collections, shutil, json, math

import pandas as pd
import numpy as np
import requests

import util3

# Defines the directory structure for the data files.
# Is necessary because we sometimes run (a) from the command line in the source
# directory or (b) as a cronjob from an arbitrary directory.
# In the latter case we have to have an absolute path.
SUPERDIR_PATH = os.path.abspath( os.path.join( os.path.abspath( __file__ ), '../..' ) )

class WebSourceException( Exception ): pass

def is_nan( x ):
    try:
        return math.isnan( float(x) )
    except:
        return False

############################################################################################
############################################################################################
# Series
############################################################################################
############################################################################################

class Series:
    Name2Instance = {}
    def __init__( self, name_internal, hide_box, hide_name ):
        self.hide_box = hide_box
        self.hide_name = hide_name
        self.name_internal = name_internal
        parts = self.name_internal.rsplit('_',1)
        self.name_external = '%s [%s]' % ( parts[0], parts[1].upper() )
        self.name_external_simplest = parts[0].title()
        self.source_instances = []      # set in < Add > classmethod
        self._geo_tree = None           # set in < geo_tree > method
    
    def timedname( self, alpha=False, formal=False, spaced=False, compact=False ):
        # Initially cached the value of < localtime > in a slot, but this prevented the
        # value from updating when a separate process (e.g. cron) did -g update option.
        # From: https://stackoverflow.com/questions/12458595/convert-timestamp-since-epoch-to-datetime-datetime
        mtime = max([ os.path.getmtime( source.path_to_content_file() ) 
                      for source in self.source_instances ])
        localtime = time.localtime(mtime)
        if alpha:   return time.strftime( '%d%b%y %H:%M %Z',      localtime )
        if formal:  return time.strftime( '%Y-%m-%d-%H.%M.%S-%Z', localtime )
        if spaced:  return time.strftime( '%Y-%m-%d %H:%M:%S %Z', localtime )
        if compact: return time.strftime( '%y%m%d.%H%M%S',        localtime )
        raise WebSourceException( 'No argument to <timed name>.' )

    def __repr__( self ):
        return '<%s.%s>' % ( self.__class__.__name__, self.name_internal )

    @classmethod
    def Add( _, series_name, source ):
        series = Series.Name2Instance.get(series_name, None)
        if series is None:
            series =  Series( series_name, source.hide_box, source.hide_name )
            Series.Name2Instance[ series.name_internal ] = series
        series.source_instances.append( source )
        return series

    @classmethod
    def AlphaList( _ ):
        return sorted( Series.Name2Instance.values(), key=lambda o: o.name_external )

    @classmethod
    def GetSeries( _, name_internal ):
        return Series.Name2Instance[ name_internal ]

    def geo_tree( self ):
        if self._geo_tree is None:
            self._geo_tree = {}
            #print 838323, self.source_instances
            if self.source_instances:
                # Uses Assumption 3774941014: generates fresh copy every time
                self._geo_tree = self.source_instances[0].get_geotree()
                for source in self.source_instances[1:]:
                    self._geo_tree = merge_dicts(self._geo_tree,source.get_geotree())
        return self._geo_tree

    def geo_tree_as_json_str( self ):
        #print 652794, self, self.source_instances
        return json.dumps( self.geo_tree() )

    def get_df( self, geo_triple ):
        # Is called from main Flask page-building file.
        nation, state, county = geo_triple
        df_list = [ source.get_df3_from_disk( None if nation==EMPTY else nation, 
                                              None if state ==EMPTY else state, 
                                              None if county==EMPTY else county ) 
                    for source in self.source_instances ]
        df_list = [ df for df in df_list if df is not None ]
        if len( df_list ) != 1:
            raise WebSourceException( 'Found no data source for %s / %s' 
                                      % ( self.name_internal, geo_triple ) )
        return df_list[0]        

def merge_dicts(a, b, path=None):
    # Adapted from: 
    # https://stackoverflow.com/questions/7204805/how-to-merge-dictionaries-of-dictionaries
    # The adaptation resolves conflicts by merging lists.
    # We know that the third level is always a list.
    "merges b into a"
    if path is None: path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge_dicts(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass # same leaf value
            else:
                #print 38832, a[key], b[key]
                a[key] += b[key] #raise Exception('Conflict at %s' % '.'.join(path + [str(key)]))
        else:
            a[key] = b[key]
    return a

############################################################################################
############################################################################################
# Source
############################################################################################
############################################################################################

class Source:
    Instances = []
    Seriesname2Sourceobjs = collections.defaultdict( list )
    def __init__( self ):
        Source.Instances.append( self )
        self.geoname2path = {}
        for seriesname_internal in self.series_names:
            Source.Seriesname2Sourceobjs[ seriesname_internal ].append( self )
            Series.Add( seriesname_internal, self )
        self.init2()

    #     @classmethod
    #     def ReadPossibleGeos( _ ):
    #         for source in Source.Instances:
    #             for path in glob.glob( source.spraypath()+'/*' ):
    #                 geo_name = os.path.splitext( os.path.basename( path ) )[0]
    #                 source.geoname2path[ canonize_geoname( geo_name ) ] = path

SPRAY = 'spray'
USA = 'USA'
EMPTY = ''

class DiskFile0:
    # vDATA0
    #    nyt_us_counties_20-05-02-1252-PT_< time.time() >.csv
    #    jhu_us_counties_20-05-02-1631-PT_< time.time() >.csv
    # vDATA1
    #    nyt_us_counties
    #        contents.csv
    #        digest.txt
    #        geotree.json
    #        spray
    #            alabama
    #            alaska
    #        when=20-05-02-1252-PT.txt (contents = time.time() value )
    #    jhu_us_counties
    #        contents.csv
    #        digest.txt
    #        geotree.json
    #        spray
    #            alabama
    #            alaska
    #        when=20-05-02-1631-PT.txt (contents = time.time() value )
    # vDATAx
    #    jhu_us_counties_< time.time() >
    #        contents.csv
    #        digest.txt
    #        geotree.json
    #        spray
    #            alabama
    #            alaska
    #        when=20-05-02-1631-PT.txt (contents = time.time() value )

    dirpath0 = os.path.join( SUPERDIR_PATH, 'vDATA0' )
    dirpath1 = os.path.join( SUPERDIR_PATH, 'vDATA1' )
    dirpathx = os.path.join( SUPERDIR_PATH, 'vDATAx' )
    contents_filename = 'contents.csv'
    digest_filename   = 'digest.txt'
    geotree_filename  = 'geotree.json'
    whenfile_name_fmt = 'when=%s.txt'
    now_fmt = '%y-%m-%d-%H%M-%z'

    def pre_spray( self, dirname, new_contents, new_digest ):
        digest_path = os.path.join( self.dirpath1, dirname, self.digest_filename )
        if os.path.isfile( digest_path ):
            with open( digest_path, 'r' ) as f:
                old_digest = f.read().strip()
                if old_digest == new_digest:
                    return None, None, None, None
        timetime = str( int( 100 * time.time() ) )
        now_str = datetime.datetime.now().strftime( self.now_fmt )
        dirpath_temp = os.path.join( self.dirpathx, '%s_%s' % ( dirname, timetime ) )
        dirpath_final = os.path.join( self.dirpath1, dirname )
        spray_path = os.path.join( dirpath_temp, SPRAY )
        if not os.path.isdir( self.dirpath0 ): os.makedirs( self.dirpath0 )
        if not os.path.isdir( self.dirpath1 ): os.makedirs( self.dirpath1 )
        if not os.path.isdir( self.dirpathx ): os.makedirs( self.dirpathx )
        if not os.path.isdir( spray_path    ): os.makedirs( spray_path    )
        contents_path = os.path.join( dirpath_temp, self.contents_filename )
        with open( contents_path, 'wb' ) as f:
            f.write( new_contents )
        with open( os.path.join( dirpath_temp, self.digest_filename ), 'wb' ) as f:
            f.write( new_digest )
        with open( os.path.join( dirpath_temp, self.whenfile_name_fmt % now_str ), 'wb' ) as f:
            f.write( timetime )
        archive_filename = '%s_%s_%s%s' % ( dirname, now_str, timetime, 
                              os.path.splitext( self.contents_filename )[1] )
        with open( os.path.join( self.dirpath0, archive_filename ), 'wb' ) as f:
            f.write( timetime )
        return contents_path, dirpath_temp, dirpath_final, spray_path

    def spraypath( self ):
        return os.path.join( self.dirpath1, self.dirname, SPRAY )

    def get_geotree( self ):
        # Provides Assumption 3774941014: generates fresh copy every time
        with open( os.path.join( self.dirpath1, self.dirname, self.geotree_filename ), 'r' ) as f:
            dikt = json.load( f )
            #print 737325, dikt
            return dikt

    def path_to_content_file( self ):
        return os.path.join( self.dirpath1, self.dirname, self.contents_filename )

class WebSource( Source, DiskFile0 ):
    WebSourcesToPoll = []

    def init2( self ):
        WebSource.WebSourcesToPoll.append( self )
    
    @classmethod
    def Poll( cls, is_production=False ):
        # Use NilException when debugging because it allows full traceback to be printed.
        class NilException(Exception): pass
        exception_class = Exception if is_production else NilException
        all_ok = True
        for instance in WebSource.WebSourcesToPoll:
            source_printname = instance.__class__.__name__
            print 'Starting check of', source_printname
            try:
                instance.poll()
                print 'Finished check of', source_printname
            except exception_class:
                print 'Failed with check of', source_printname
                all_ok = False
        return all_ok
    
    def poll( self ):
        try:
            content, digest = self._grab_contents_from_web()
            contents_path, dirpath_temp, dirpath_final, spray_dirpath = self.pre_spray( self.dirname, content, digest )
            if contents_path is not None:
                source_printname = self.__class__.__name__
                print 'Starting spray of', source_printname, '***'
                geotree = self.spray_and_geotree( content, spray_dirpath )     # raises Exception if problem
                with open( os.path.join( dirpath_temp, self.geotree_filename ), 'w' ) as f:
                    json.dump( geotree, f )
                if os.path.isdir( dirpath_final ):
                    os.rename( dirpath_final, dirpath_final+'xx' )
                    os.rename( dirpath_temp, dirpath_final )      # Atomic on Unix
                    shutil.rmtree( dirpath_final+'xx' )
                else:
                    os.rename( dirpath_temp, dirpath_final )      # Atomic on Unix
                print 'Finished spray of', source_printname
        except Exception as e:
            print 'Failed with spray of', source_printname,   # Send Slack message?
            print '******', e
            raise

    def _grab_contents_from_web( self ):
        r = requests.get( self.url )
        #print 4949, r.content
        m = md5.new()
        m.update( r.content )
        digest = m.hexdigest()
        return r.content, digest

    def dataframe_from_csv_string( self, s ):
        f = StringIO.StringIO()
        f.write( s )
        f.seek(0)
        dataframe = pd.read_csv( f )
        return dataframe
   
    def _slurp_df_from_disk( self, geo_name ):
        path = self.geoname2path.get( canonize_geoname( geo_name ), None )
        path = os.path.join( self.dirpath1, self.dirname, SPRAY, geo_name + '.csv' )
        #print 479244, path
        if path is None:
            raise Exception( 'No data for %s / %s' % ( self.series_names, geo_name ) )
        return pd.read_csv( path )

def canonize_geoname( s ):
    return s.lower()

def unique2filename( unique ):
    return unique + '.csv'

class CTP( WebSource ):
    series_names = [ 'cases_CTP', 'deaths_CTP', 'tests_CTP' ]
    renames = { 'positive':'cases_CTP', 'death':'deaths_CTP', 'totalTestResults': 'tests_CTP', 'hospitalizedCumulative': 'hosp_admits_CTP',
                'onVentilatorCumulative': 'new_vents_CTP', 'inIcuCumulative': 'icu_admits_CTP', 'date': 'YYYYMMDD', 'state': 'k8state' }
    hide_box = ['USA',]
    hide_name = ['USA',]
    full_source_sortnum_and_name = (3, 'Covid Tracking Project')

class CTP_States( CTP ):
    url = 'https://covidtracking.com/api/v1/states/daily.csv'
    dirname = 'ctp_us_states'
    spray_field = 'k8state'
    n_geos_in_spec = 1

    def spray_and_geotree( self, content, spray_dirpath ):
        df = self.dataframe_from_csv_string( content )
        df.rename(columns=self.renames, inplace=True )
        df = df.replace({ 'k8state': util3.STATE_ABBREV })
        df.sort_values( 'YYYYMMDD', ascending=True, inplace=True )
        geotree = {}
        for unique in df[ self.spray_field ].unique():
            outpath = os.path.join( spray_dirpath, unique2filename(unique) )
            state_df = df[ df[ self.spray_field ]==unique ]
            if len( self.series_names ) == 1:
                # Expression on right gave warning if performed with < inplace=True >.
                state_df = state_df.dropna( subset=self.series_names, how='all', inplace=False )
            # Don't write a file unless there is actually some data to write
            if len(state_df)>1:                 # >1 because we need that many for a trend
                state_df.to_csv( outpath )
                geotree[ unique ] = EMPTY
        return { USA: geotree }

    def get_df3_from_disk( self, nation, state, county ):
        df = self._slurp_df_from_disk( state )
        #print 8803, df.head()
        df.index = pd.to_datetime( df.YYYYMMDD, format='%Y%m%d' )
        return df

class CTP_Hosp( CTP_States ):
    series_names = [ 'hosp_admits_CTP', ]
    dirname = 'ctp_states_hosp'

class CTP_Vent( CTP_States ):
    series_names = [ 'new_vents_CTP', ]
    dirname = 'ctp_states_vent'

class CTP_ICU( CTP_States ):
    series_names = [ 'icu_admits_CTP', ]
    dirname = 'ctp_states_icu'

class NYT( WebSource ):
    series_names = [ 'cases_NYT', 'deaths_NYT' ]
    renames = { 'cases':'cases_NYT', 'deaths':'deaths_NYT', 'county':'k8county', 'state':'k8state' }
    hide_box = ['USA',]
    hide_name = ['USA',]
    full_source_sortnum_and_name = (2, 'New York Times')

    def spray_and_geotree( self, content, spray_dirpath ):
        df = self.dataframe_from_csv_string( content )
        df.rename(columns=self.renames, inplace=True )
        geotree = {}
        for unique in df[ self.spray_field ].unique():
            outpath = os.path.join( spray_dirpath, unique2filename(unique) )
            state_df = df[ df[ self.spray_field ]==unique ]
            state_df.to_csv( outpath )
            geotree[ unique ] = self.make_county_list( state_df )
        return { USA: geotree }
 
class NYT_Counties( NYT ):
    url = 'https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv'
    dirname = 'nyt_us_counties'
    spray_field = 'k8state'
    hemi1_field = 'k8county'
    #lookups = 'NMU'

    def make_county_list( self, state_df ):
        return list( state_df[ self.hemi1_field ].unique() )

    def get_df3_from_disk( self, nation, state, county ):
        if state and county:
            df = self._slurp_df_from_disk( state )
            df.index = pd.to_datetime( df.date )
            return df[ df[self.hemi1_field]==county ]

class NYT_States( NYT ):
    url = 'https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-states.csv'
    dirname = 'nyt_us_states'
    spray_field = 'k8state'
    n_geos_in_spec = 1
    #lookups = 'EMU'

    def make_county_list( self, state_df ):
        return [ EMPTY, ]

    def get_df3_from_disk( self, nation, state, county ):
        if state and not county:
            df = self._slurp_df_from_disk( state )
            #print 8803, df.head()
            df.index = pd.to_datetime( df.date )
            #print 8804, df.head()
            return df

class JHU( WebSource ):
    hide_box = ['USA',]
    hide_name = ['US']
    full_source_sortnum_and_name = (1, 'Johns Hopkins University')

    def spray_and_geotree( self, content, spray_dirpath ):
        df = self.dataframe_from_csv_string( content )
        df.rename(columns=self.renames, inplace=True )
        for colname in df.columns:
            if (colname[0] not in '0123456789') and (colname not in (self.hemi1_field,self.spray_field)):
                del df[colname]
        geotree_pairs = []
        for unique in df[ self.spray_field ].unique():
            outpath = os.path.join( spray_dirpath, unique2filename(unique) )
            #df1 = self._transpose( df[ df[ self.spray_field ]==unique ] )
            df1 = df[ df[ self.spray_field ]==unique ]
            df1.to_csv( outpath )
            geotree_pairs.append( (unique, list( df1[self.hemi1_field].unique() ) ) )
        return self.make_geotree( geotree_pairs )

    def _transpose_row_neo( self, df0, series_name, geo_name ):
        # Each row has format: hemi1, hemi2, date1, date2, date3, ....
        # So iterate across [2:] to drop hemi2, which is not needed because is in filename.
        df_rows = []
        for _, row in df0.iterrows():
            for date, n in zip( df0.columns[3:], row[3:] ):
                df_rows.append( ( date, geo_name, n ) )
        df = pd.DataFrame( df_rows, columns=['DATESTRING', 'REFNAME', series_name] )
        df.index = pd.to_datetime( df.DATESTRING )
        #print 8381203, df.columns
        #print df
        return df

    def sum_df( self, df ):
        # Assumption 4729424: Non-date columns cannot start with digit
        for first_date, colname in enumerate( df.columns ):
            if colname[0] in '0123456789': break
        series = df.sum( numeric_only=False )[ first_date: ]  # < True > would strip dates
        df2 = pd.DataFrame( series )
        df2.index = pd.to_datetime( df2.index )
        df2.columns = self.series_names[:1]
        #print 7333, type(df), type(df2), df2.head()
        return df2

class JHU_Cases_Counties( JHU ):
    url = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_US.csv'
    dirname = 'jhu_us_cases'
    renames = { 'Province_State':'k8state', 'Admin2':'k8county' }
    spray_field = 'k8state'    # Assumption 4729424: Cannot start with digit
    hemi1_field = 'k8county'   # Assumption 4729424: Cannot start with digit
    
    series_names = ['cases_JHU',]
    #lookups = 'NMU'

    def make_geotree( self, state_countylist_pairs ):
        return { USA: { state:countylist for state, countylist in state_countylist_pairs } }

    def get_df3_from_disk( self, nation, state, county ):
        if state and (nation==USA):
            df = self._slurp_df_from_disk( state )
            if county:
                df = df[ df[self.hemi1_field]==county ]
                df = self._transpose_row_neo( df, self.series_names[0], county )
            else:
                # State total is sum of all rows for the state.
                # The < sum > method yields a dataframe, includes non-numeric cells, too.
                # (Saying numeric=True would yield series sans dates -- useless.)
                #
                # However, we'll need to remove cells that don't derive from a date.
                # Assumption 4729424: Non-date columns cannot start with digit
                for first_date, colname in enumerate( df.columns ):
                    if colname[0] in '0123456789': break
                series = df.sum( numeric_only=False )[first_date:]  # < True > would strip dates
                df2 = pd.DataFrame( series )
                df2.index = pd.to_datetime( df2.index )
                df2.columns = self.series_names[:1]
                #print 7333, type(df), type(df2), df2.head()
                df = df2
            return df

class JHU_Cases_Nations( JHU ):
    url = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv'
    dirname = 'jhu_nation_cases'
    renames = { 'Province/State':'k8state', 'Country/Region':'k8country' }
    spray_field = 'k8country'
    hemi1_field = 'k8state'
    
    series_names = ['cases_JHU',]
    #lookups = 'EOM'

    def make_geotree( self, nation_regionlist_pairs ):
        return { nation: { (EMPTY if is_nan( region ) else region): EMPTY
                           for region in regionlist }
                 for nation, regionlist in nation_regionlist_pairs }

    def get_df3_from_disk( self, nation, state, county ):
        #print 8880, self, nation, state, county
        if (not county) and (nation != USA):
            df = self._slurp_df_from_disk( nation )
            #print 8881,  nation, state, county, df
            if state:
                df2 = df[ df[self.hemi1_field]==state ]
                df = self._transpose_row_neo( df2, self.series_names[0], state )
            else:
                df2 = df[ df[self.hemi1_field].isnull() ]
                if len(df2)==0:
                    df = self.sum_df( df )
                else:
                    df = self._transpose_row_neo( df2, self.series_names[0], state )
            #print 8883,  nation, state, county, df
            return df

    def get_df3_from_diskOOOO( self, nation, state, county ):
        #print 8880, self, nation, state, county
        if (not county) and (nation != USA):
            df = self._slurp_df_from_disk( nation )
            #print 8881,  nation, state, county, df
            df = df[ df[self.hemi1_field]==state ] if state else df[ df[self.hemi1_field].isnull() ]
            #print 8883,  nation, state, county, df
            df = self._transpose_row_neo( df, self.series_names[0], state or nation )
            return df

class JHU_Deaths_Counties( JHU_Cases_Counties ):
    url = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_US.csv'
    dirname = 'jhu_us_deaths'
    
    series_names = ['deaths_JHU',]
    #lookups = 'NMU'

class JHU_Deaths_Nations( JHU_Cases_Nations ):
    url = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv'
    dirname = 'jhu_nation_deaths'
    
    series_names = ['deaths_JHU',]
    #lookups = 'EOM'

CTP_States()
CTP_Hosp()
CTP_Vent()
CTP_ICU()
NYT_Counties()
NYT_States()
JHU_Cases_Counties()
JHU_Cases_Nations()
JHU_Deaths_Counties()
JHU_Deaths_Nations()

def check_for_new_web_sources( is_production=False ):
    # < is_production > affects only error notifications
    return WebSource.Poll( is_production=is_production )

if __name__=='__main__':
    check_for_new_web_sources()
    #Source.ReadPossibleGeos()
