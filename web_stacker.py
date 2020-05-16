import math

import numpy as np
import matplotlib
matplotlib.use('Agg')                       # Cannot be TkAgg to run in web server
import matplotlib.pyplot as plt

import web_graphline as gl
import util3

LN2x100 = 100*math.log(2)
PIXELS_PER_PLOTLINE = 20
INCHES_PER_PLOTLINE = float(PIXELS_PER_PLOTLINE) / util3.DPI

def make_geostack( back_days, sergeo ):
    try:
        stack = Geostack( back_days, sergeo, sergeo.smooth( 7 ) )
    except RuntimeError:
        stack = Geostack( back_days, sergeo )
    return stack

class Geostack:
    n_windows = 7                       # How many days back we calculate change-rates
    def __init__( self, window_sz, *sergeo_tuple ):
        sergeo1 = sergeo_tuple[0]
        self.sergeo_tuple = sergeo_tuple
        self.labeltxt = sergeo1.geo_name
        util3.log( 'Stacker calc for:', self.labeltxt )

        self._layers = [ Layer( [gso.subseq(-i, -i+window_sz ) for gso in self.sergeo_tuple] )
                         for i in range( window_sz, window_sz + self.n_windows ) ]
        # Add 1 line for text label and 1 line for blank line below
        self.n_plotlines = 1 + 1 + len( self._layers )
        self.is_last = False     # Set True elsewhere, maybe
        self.series_nameTex = sergeo1.series_name_tex
        self.mean_of_raw = sergeo1.geo_series.mean()
        
        self.left_ylim = None
        self.solo_ax_position = None
 
    def max_min_pct( self, min0, max0 ):
        for layer in self._layers:
            min0 = min( [ min0, ] + layer.pcts )
            max0 = max( [ max0, ] + layer.pcts )
        return min0, max0

    def plot_layers( self, ax, ytop, ydelta, series_denom ):
        x = self._layers[0].midpoint_pct()
        ax.text( x, ytop, self.labeltxt, horizontalalignment='center', va='center' )
        y = ytop - ydelta
        n = float( len( self._layers ) )
        linewidth = max( 0.5, 17.5 * self.mean_of_raw / series_denom )
        linewidth = min( linewidth, 15.5 )
        connects_x, connects_y = [], []
        for i, layer in enumerate( self._layers ):
            kolor = ( 0,0,0, 1-i/n )                        # increasing transparency
            smooth_pct = layer.plot( ax, y, kolor, linewidth )
            if smooth_pct is not None:
                connects_x.append( smooth_pct )
                connects_y.append( y )
            y -= ydelta
        ax.plot( connects_x, connects_y, 'b' )
        return y-ydelta

    def waveform( self, ax ):
        linewidths = (1,3)
        for linewidth, gso in zip( linewidths, self.sergeo_tuple ):
            gso.graphline(ax,{}).plot( linewidth=linewidth )
        for linewidth, point in zip( linewidths, self._layers[0]._points ):  # _layer[0] = most recent day 
            if point.extrapolated:
                point.extrapolated.graphline(ax,{}).plot( linewidth=linewidth )
                y = point.extrapolated.geo_series.iloc[-1]
                x = point.extrapolated.geo_series.index[-1]
                ax.plot([x,],[y,],point.linestyle)
        ax.yaxis.tick_right()
        ax.legend([ self.labeltxt, ], loc='upper left' )
        highest = self.sergeo_tuple[0].maxval()
        ymax = min( 2.5*highest, ax.get_ylim()[1] )
        if not math.isnan( ymax ):
            ax.set_ylim([0,ymax])
        if self.is_last:
            ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%d%b'))
            ax.xaxis.set_major_locator(plt.MultipleLocator( 3 ))
            # See: https://stackoverflow.com/questions/10998621/rotate-axis-text-in-python-matplotlib
            plt.xticks(rotation=45, horizontalalignment='right')
        else:
            ax.set_xticks([])
        ax.text( ax.get_xlim()[0], sum(ax.get_ylim())/2., ' \n\n'+self.series_nameTex, 
                 horizontalalignment='center', verticalalignment='center', rotation=90,
                 color='grey' )

#     def waveformB( self, ax ):                          # Useful for debugging. Set < self.n_windows > greater than < window_sz > for best results
#         self.geo_series1.graphline(ax,{}).plot()
#         #self._layers[0]._points[0].geo_series.graphline(ax,{}).plot()
#         self._layers[0]._points[1].geo_series.graphline(ax,{}).plot( linewidth=3 )
#         self._layers[0]._points[1].extrapolated.graphline(ax,{}).plot( linewidth=3 )
#         #self._layers[-1]._points[0].geo_series.graphline(ax,{}).plot()
#         self._layers[-1]._points[1].geo_series.graphline(ax,{}).plot( linewidth=3 )
#         self._layers[-1]._points[1].extrapolated.graphline(ax,{}).plot( linewidth=3 )
#         print 6606,  self._layers[-1]._points[1].extrapolated.extrapolation_doubling,  self._layers[0]._points[1].extrapolated.extrapolation_doubling
#         print 6607,  self._layers[-1]._points[1].dub,  self._layers[0]._points[1].dub
#         #point1, point2 = layer1._points
#         #point2.extrapolated.graphline(ax,{}).plot( linewidth=3 )
#         ax.yaxis.tick_right()
#         ax.legend([ self.labeltxt, ], loc='upper left' )
#         if self.is_last:
#             ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%d%b'))
#             ax.xaxis.set_major_locator(plt.MultipleLocator( 3 ))
#             # See: https://stackoverflow.com/questions/10998621/rotate-axis-text-in-python-matplotlib
#             plt.xticks(rotation=45, horizontalalignment='right')
#         else:
#             ax.set_xticks([])

class Layer:
    zorder=250                  # Frontmost, assuming no higher zorder specified

    def __init__( self, short_series_list ):
        self._points = [ klass( geo_series ) 
                         for geo_series, klass in zip( short_series_list, ( PointRaw, PointSmooth ) )  ]
        self.pcts = filter( None, [ point.pct for point in self._points ] )

    def midpoint_pct( self ):
        return ( min(self.pcts) + max(self.pcts) ) / 2. if self.pcts else 0

    def plot( self, ax, y, kolor, linewidth ):
        if self.pcts:
            max_pct = max( self.pcts )
            min_pct = min( self.pcts )
            for point in self._points:
                ax.plot( [point.pct,], [y,], point.linestyle, color=kolor, zorder=self.zorder )
                ha = 'left' if point.pct == max_pct else ('right' if point.pct==min_pct else None )
                if ha:
                    ax.text( point.pct, y, '  %.1f%%  ' % point.pct, 
                             horizontalalignment=ha, va='center', color=kolor, zorder=self.zorder )
            if max_pct != min_pct:
                if linewidth < 3.5:
                    ax.plot( [min_pct, max_pct], [y,y], color=kolor, zorder=self.zorder,
                             linewidth = linewidth )
                else:
                    y1, y2 = y-linewidth/2., y+linewidth/2.
                    ax.fill( [min_pct, max_pct, max_pct, min_pct, min_pct ], [y1,y1,y2,y2,y1],
                             color=kolor, zorder=self.zorder )
        else:
            ax.text( 0, y, '< omitted >', color=kolor, verticalalignment='center', zorder=self.zorder )
        smooth_pcts = [ point.pct for point in self._points 
                        if isinstance(point,PointSmooth) and (point.pct is not None) ]
        return smooth_pcts[0] if len(smooth_pcts)==1 else None

class Point:
    forward_days = 5
    def __init__( self, geo_series ):
        self.geo_series = geo_series
        back_days = self.geo_series.datalength()-1
        self.extrapolated = None
        self.dub = None
        self.pct = None
        if self.geo_series.datalength() > 2:  # Otherwise fitting a 2-parm model breaks
            try:
                self.extrapolated = self.geo_series.extrapolate( back_days, self.forward_days, exponential=True )
                self.dub = self.extrapolated.extrapolation_doubling
                self.pct = 0 if self.dub==0 else LN2x100 / self.dub
            except RuntimeError:
                pass

class PointRaw( Point ):
    linestyle = 's'

class PointSmooth( Point ):
    linestyle = 'o'

class Stacklist:
    def __init__( self, stackobj_list ):
        self.stackobjs = stackobj_list
        self.stackobjs[-1].is_last = True
    
    def pct_bounds( self ):
        # Returns the xlim for the main "vertical" plot.
        # Also returns the doubling-time locations and labels.
        pct_min = 9e9
        pct_max = -9e9
        for stack in self.stackobjs:
            pct_min, pct_max = stack.max_min_pct( pct_min, pct_max )
        pct_min = max( min(pct_min,-0.001), -40 )   # Always show some green zone
        pct_max = min( max(pct_max, 0.001),  40 )   # Always show some red-zone
        pct0 = pct_min-(pct_max-pct_min)/5.
        pct9 = pct_max+(pct_max-pct_min)/5.

        p_step = ( pct_max - pct_min ) / 11.        # Put approx. 11 tick marks x-axis
        if pct0*pct9>0:
            pp = np.arange( pct_min, pct_max, p_step )
        else:
            pp1 = np.arange( -p_step, pct_min-p_step, -p_step )
            pp2 = np.arange( p_step, pct_max+p_step, p_step )
            pp = list(pp1) + list(pp2)

        def p2d(p): return 0 if p==0 else LN2x100/p  # convert pct to day
        def d2p(d): return 0 if d==0 else LN2x100/d  # convert day to pct
        dd_final = [ round( p2d(p) ) for p in pp ]
        pp_final = [ d2p( d ) for d in dd_final ]

        return pct0, pct9, zip( pp_final, dd_final )

    def layout( self, fig, ax ):
        n_plotlines  = sum([ stack.n_plotlines for stack in self.stackobjs ])
        # Subtract 1 line for blank line beneath bottom-most county
        y8 = (n_plotlines-1)*PIXELS_PER_PLOTLINE
        y9 = y8 + 0.5 * PIXELS_PER_PLOTLINE
        y0 = 0
        ylim = ( y0, y9 )
        ax_ht_inches = float(y9-y0) / util3.DPI
        figA_wd_inches = 6.
        figB_wd_inches = 6.
        fig_wd_inches = figA_wd_inches + figB_wd_inches
        left_inches = 0.3
        right_inches = 0.53
        top_inches = 1.15
        bot_inches = 0.53
        fig_ht_inches = top_inches + ax_ht_inches + bot_inches
        ax_position = ( left_inches / fig_wd_inches,
                        bot_inches / fig_ht_inches,
                        (figA_wd_inches - left_inches) / fig_wd_inches,  # ax width fraction
                        (fig_ht_inches - top_inches - bot_inches) / fig_ht_inches )
        def y2inches(y,j=1): return j*bot_inches + ax_ht_inches * (y-y0) / (y9-y0)
        #print 40404, fig_ht_inches, '=', top_inches, ax_ht_inches, bot_inches, fig_ht_inches-top_inches-ax_ht_inches-bot_inches
        #print 50505, y2inches(y9), y2inches(y8), y2inches(y0), fig_ht_inches, fig_ht_inches-top_inches

        solo_left = ax_position[0]+ax_position[2]
        solo_width = 1 - solo_left - right_inches/fig_wd_inches

        fig.set_size_inches( fig_wd_inches, fig_ht_inches )
        ax.set_position( ax_position )

        bar_bot_fraction = (fig_ht_inches-.29)/fig_ht_inches
        axbar_pos = (0, bar_bot_fraction, 1, 1-bar_bot_fraction)

        return y0, y8, y9, solo_left, solo_width, y2inches, fig_ht_inches, axbar_pos
        

def stackerX( sergeos, series_name, dataset_when, pathname ):
    back_days = 14
    forward_days = 10
    #
    # Create stack instance for each geo.  Determine # plotlines and extreme pcts.
    #
    stacklist = Stacklist( [ make_geostack( back_days, sergeo.diff() )
                             for sergeo in sergeos ] )
    return stacker0( {}, back_days, forward_days, series_name, stacklist, dataset_when, pathname )

def stacker0( plotdict, back_days, forward_days, series_name, stacklist, dataset_when, pathname ):
    pct0, pct9, pd_pairs = stacklist.pct_bounds()
    stacks = stacklist.stackobjs
    series_denom = sum([ stack.mean_of_raw for stack in stacks ]) / len( stacks )
    ylabel = util3.texify('daily_' + series_name)
    #
    # Draw plots.  Includes consolidated "vertical" axes + an axes for each geo.
    #
    with util3.Plot( [1], pathname=pathname ) as plot:
        ax = plot.subplot_axis(0)
        y0, y_top, y9, solo_left, solo_width, y2inches, fig_ht_inches, axbar_pos = stacklist.layout( plot.fig, ax )
        ylim = (y0,y9)
        ax.fill( [pct0,0,0,pct0,pct0], [y0,y0,y9,y9,y0], '#bbffbb', zorder=1 ) # green
        ax.fill( [pct9,0,0,pct9,pct9], [y0,y0,y9,y9,y0], '#FF7F7F', zorder=1 ) # red
        #
        # Plot the layers for each geo into the "vertical" consolidated axes.
        # Also plot the "waveform" axes for each geo.
        #
        for stack in stacks:
            util3.log( 'Stacker plot for:', stack.labeltxt )
            for pct, day in pd_pairs:
                ax.text( pct, y_top+PIXELS_PER_PLOTLINE, '%dd' % abs(day), verticalalignment='center', horizontalalignment='center', zorder=99 )
            y_bot = stack.plot_layers( ax, y_top, PIXELS_PER_PLOTLINE, series_denom )
            solo_pos = ( solo_left, 
                         y2inches(y_bot+ PIXELS_PER_PLOTLINE)/fig_ht_inches, 
                         solo_width, 
                         y2inches(y_top-y_bot,0)/fig_ht_inches )
            ax2 = plot.fig.add_axes( solo_pos )
            stack.waveform( ax2 )                   # Waveform
            y_top = y_bot
        #
        # Set up the appurtenances for the overall plot.
        #
        ax.set_xlim([ pct0, pct9 ])
        ax.set_xlabel('% Daily Change')
        ax.set_ylabel('Best = As far left as possible')
        ax.set_yticks([])
        ax.yaxis.grid(True)
        ax.set_ylim( ylim )
        for pct, day in pd_pairs:
            ax.plot( [pct,pct], ylim, 'k:', linewidth=0.5, zorder=99 )
        #    ax.text( pct, ylim[1], '%dd' % abs(day), verticalalignment='bottom', horizontalalignment='center', zorder=99 )
        ax.text( pct0, y9, 'Halving time (days)\n ',  horizontalalignment='left', va='bottom', zorder=99 )
        ax.text( pct9, y9, 'Doubling time (days)\n ', horizontalalignment='right', va='bottom', zorder=99 )
        plot.tidy_plot = False

        axbar = plot.fig.add_axes( axbar_pos )
        axbar.set_xlim([0,1])
        axbar.set_ylim([0,1])
        #axbar.set_xticks([])
        #axbar.set_yticks([])
        axbar.axis('off')
        axbar.fill( [0,1,1,0,0],[0,0,1,1,0], color='yellow' )
        axbar.text( 0.5,0.5, ylabel, fontsize=14, horizontalalignment='center', verticalalignment='center' )            
        suptitle = '%s-day Trend Fits -- Dataset of: %s --   $\\blacksquare=$raw data trend     $\\bigcirc=$smoothed data trend\nTesting volume not considered' % ( back_days, dataset_when )
        plot.fig.text( 0.5, axbar_pos[1], suptitle, fontsize=13, horizontalalignment='center', verticalalignment='top', color='grey' )
        return plot.pathname
