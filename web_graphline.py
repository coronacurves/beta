import copy
import math

import scipy.optimize
import pandas
import numpy as np

DEFAULT_LINEWIDTH = 1
DEFAULT_LINESTYLE = '-'
DEFAULT_LEFTTIME = 21
DEFAULT_LABEL_HALIGN = 'left'
DEFAULT_LABEL_VALIGN = 'center'

def stamp2daynum( timestamp ):
    return timestamp.toordinal()
    
def daynum2stamp( daynum ):
    return pandas.Timestamp.fromordinal( daynum )

def extrapolate_linear( series, days_back, days_forward ):
    base_index = series.index[-days_back-1]
    base_daynum = stamp2daynum( base_index )
    dd_actual = [ stamp2daynum(x) - base_daynum for x in series.index[-days_back-1:] ]
    yy_actual = list( series.iloc[-days_back-1:] )
    m_linear, b_linear = np.polyfit( dd_actual, yy_actual, 1 )
    #print 77477, dd_actual, yy_actual, b_linear, m_linear
    dd = dd_actual + range( dd_actual[-1]+1, dd_actual[-1]+1+days_forward )
    yy = [ m_linear*d + b_linear for d in dd ]
    #print 482043, dd
    xx = [ daynum2stamp(d+base_daynum) for d in dd ]
    return pandas.Series( yy, index=xx ), m_linear

def extrapolate_log( series, back, forward ):
    base_index = series.index[-back-1]
    base_daynum = stamp2daynum( base_index )
    dd_actual = [ stamp2daynum(x) - base_daynum for x in series.index[-back-1:] ]
    yy_actual = [ y                 for y in series.iloc[ -back-1:] ]
    # The nan checking is a band-aid because NYT Mariposa has a NaN.  Why wasn't it dropped?
    both = filter( lambda dy: not math.isnan(dy[1]), zip( dd_actual, yy_actual ) )
    dd_actual = [ d for d,y in both ]
    yy_actual = [ y for d,y in both ]
    #print 'yy_actual', yy_actual
    const = min(yy_actual)
    const = -(const-1) if const<=0 else 0
    #print 22293, min(yy_actual), const, [(y+const) for y in yy_actual ]
    yy_logged = [ math.log(y+const) for y in yy_actual ]
    m_linear, b_linear = np.polyfit( dd_actual, yy_logged, 1 )
    #print 774248, dd_actual, yy_actual, b_linear, m_linear
    p_opt, p_cov = scipy.optimize.curve_fit(lambda t,a,b: a*np.exp(b*t), dd_actual, yy_actual,  p0=None ) #[2.7**m_linear,b_linear] )
    dd = dd_actual + range( dd_actual[-1]+1, dd_actual[-1]+1+forward )
    yy = [ p_opt[0]*math.exp(p_opt[1]*d)-const for d in dd ]
    xx = [ daynum2stamp(d+base_daynum)         for d in dd ]
    #print 774299, dd, yy, math.log(2)/p_opt[1]
    return pandas.Series( yy, index=xx ), math.log(2)/p_opt[1], math.log(0.5)/p_opt[1]  # .rename_axis('extrapolated')

class SerGeo:
    def __init__( self, geo_name, df, series_name, left_time ):
        self.series_name = series_name
        self.geo_name = geo_name

        series = df[ self.series_name ]
        #print 8998, self.series_name,'\n',series
        if left_time:
            series = series.tail( left_time ) #[ series['DATADATE']>=left_time ]
        self.geo_series = series
        
        self.extrapolation_doubling = None  # Assigned if < extrapolate > exponential
        self.extrapolation_halving  = None  # Assigned if < extrapolate > exponential
        self.extrapolation_slope    = None  # Assigned if < extrapolate > linear

    @property
    def series_name_tex( self ):
        parts = self.series_name.rsplit('_',1)
        parts = [ parts[0].lower().replace('_','.'), ] + parts[1:]
        if parts[1:]:
            s = '%s $^{%s}$' % tuple(parts)
        return s

    def has_something_to_plot( self ):
        return len( self.geo_series.dropna() ) > 0

    def graphline( self, ax, plotdict ):
        if self.has_something_to_plot():
            return Graphline( ax, self, self.series_name, self.geo_series, plotdict=plotdict )
        else:
            return NilGraphline()

    def diff( self ):
        new = SerGeoCopy( self )
        new.geo_series = self.geo_series.diff()         # Is a pandas method
        new.series_name = 'daily_' + self.series_name
        return new

    #     def diffnorm( self ):                               # "norm" = normalize
    #         new = SerGeoCopy( self )
    #         numerator = self.geo_series.diff()
    #         denominator = self.geo_series[1:].astype(float)
    #         new.geo_series = numerator / denominator
    #         new.series_name = 'diffnorm_' + self.series_name
    #         return new

    def smooth( self, window_width ):
        #from pandas.stats.moments import ewma
        new = SerGeoCopy( self )
        #new.geo_series = ewma( self.geo_series, span=5 )
        #new.geo_series = self.geo_series.ewm(span=3)
        new.geo_series = self.geo_series.ewm(span=window_width,adjust=True).mean()
        new.series_name = 'smooth_' + self.series_name
        return new

    def as_denominator( self, numerator ):
        new = SerGeoCopy( self )
        new.geo_series = ( numerator.geo_series / self.geo_series.astype(float) ).replace([np.inf, -np.inf], np.nan).dropna()
        #print 822222, new.geo_series
        #print 822223, new.geo_series.replace([np.inf, -np.inf], np.nan).dropna()
        new.series_name = 'quotient_' + self.series_name
        return new

    def extrapolate( self, days_back, days_forward, exponential ):
        new = SerGeoCopy( self )
        if exponential:
            #print 50555, self.series_name, self.geo_name, self.geo_series
            new.geo_series, new.extrapolation_doubling, new.extrapolation_halving = \
                              extrapolate_log( self.geo_series, days_back, days_forward )
        else:
            new.geo_series, new.extrapolation_slope = extrapolate_linear( self.geo_series, days_back, days_forward )
        return new

    def subseq( self, a, b ):
        new = SerGeoCopy( self )
        # Special case for zero because extrapolation likes to use < subseq[-len:0] >.
        new.geo_series = self.geo_series[a:] if b==0 else self.geo_series[a:b]
        return new

    def datalength( self ):
        return len( self.geo_series )

    def maxval( self ):
        return self.geo_series.max()

class SerGeoCopy( SerGeo ):
    def __init__( self, original_geoseries ):
        self.__dict__ = copy.copy( original_geoseries.__dict__ )

class Graphline:
    def __init__( self, ax, geo_series_obj, series_name, pandas_series, plotdict={} ):
        self.ax = ax
        self.gso = geo_series_obj
        self.series_name = series_name
        self.series = pandas_series
        self.plotdict = plotdict

    def fill( self, left_time ):
        pass
    
    def plot( self, linestyle=None, linewidth=None, xxxxxlabel_str='' ):
        self.ax.plot( self.series, 
            linestyle or self.plotdict.get('linestyle',DEFAULT_LINESTYLE), 
            linewidth=linewidth or self.plotdict.get('linewidth', DEFAULT_LINEWIDTH),
            )
        self.ax.js_has_t_graph = True
        return self
    
    def plabel( self, text, **kwargs ):  
        # kwargs = all kwargs for < axis.text() >
        x = self.series.index[-1]
        y = self.series.iloc[-1]
        graphlabel = Graphlabel( self.ax, x, y, text, kwargs )
        self.ax.js_labelleds.append( graphlabel )
        return graphlabel
       
    def label_point_y( self ):
        return None if self.label_point is None else self.label_point[1]

class NilGraphline( Graphline ):
    def __init__( self ):
        pass
    def plot( self, *_1, **_2 ):
        return self
    def plabel( self, *_1, **_2):
        return NilGraphlabel()

class Graphlabel:
    def __init__( self, ax, x, y, text, kwargs ):
        self.x = x
        self.y = y
        self.ax = ax
        self.text = text
        self.kwargs = kwargs
    
    def go( self ):
        self.ax.text( self.x, self.y, ' '+self.text, **self.kwargs )

class NilGraphlabel( Graphlabel ):
    def __init__( self, *_1, **_2 ):
        pass
    def go( *_1, **_2 ):
        pass

class GraphlinePair:

    def __init__( self, series1, series2 ):
        self.series1 = series1
        self.series2 = series2

    def linkup( self ):
        pass

    def fill_between_series( self ):
        pass
    
    def crosshatch( self ):
        pass

class GraphlineN:

    def __init__( self, *graphlines ):
        self.graphlines = list( graphlines )
    
    def add1( self, graphline ):
        self.graphlines.append( graphline )
    
    def draw_labels( self, ax ):
        # get ax size in inches
        # get ylim
        # figure minimum y-separation
        ylim = ax.get_ylim()
        highest_at_top = ylim[1] > ylim[0]
        yy = [ ( gl, gl.label_point_y() ) 
               for gl in self.graphlines 
               if gl.label_point_y() is not None ]
        yy.sort( key=lambda pair: pair[1], reverse=highest_at_top )
        