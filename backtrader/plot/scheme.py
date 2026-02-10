#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
#
# Copyright (C) 2015-2023 Daniel Rodriguez
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from __future__ import absolute_import, division, print_function, unicode_literals

# ---------------------------------------------------------------------------
# Color palettes
# ---------------------------------------------------------------------------

# Modern palette - high contrast, colorblind-friendly, visually harmonious
# Based on Matplotlib's "tab10" categorical palette (CSS hex values)
modern10 = [
    "#1f77b4",  # 0  muted blue
    "#ff7f0e",  # 1  safety orange
    "#2ca02c",  # 2  cooked asparagus green
    "#d62728",  # 3  brick red
    "#9467bd",  # 4  muted purple
    "#8c564b",  # 5  chestnut brown
    "#e377c2",  # 6  raspberry yogurt pink
    "#7f7f7f",  # 7  middle gray
    "#bcbd22",  # 8  curry yellow-green
    "#17becf",  # 9  blue-teal
]

modern10_light = [
    "#aec7e8",  # 0
    "#ffbb78",  # 1
    "#98df8a",  # 2
    "#ff9896",  # 3
    "#c5b0d5",  # 4
    "#c49c94",  # 5
    "#f7b6d2",  # 6
    "#c7c7c7",  # 7
    "#dbdb8d",  # 8
    "#9edae5",  # 9
]

# Legacy palettes (kept for backward compatibility)
tableau20 = [
    "steelblue",  # 0
    "lightsteelblue",  # 1
    "darkorange",  # 2
    "peachpuff",  # 3
    "green",  # 4
    "lightgreen",  # 5
    "crimson",  # 6
    "lightcoral",  # 7
    "mediumpurple",  # 8
    "thistle",  # 9
    "saddlebrown",  # 10
    "rosybrown",  # 11
    "orchid",  # 12
    "lightpink",  # 13
    "gray",  # 14
    "lightgray",  # 15
    "olive",  # 16
    "palegoldenrod",  # 17
    "mediumturquoise",  # 18
    "paleturquoise",  # 19
]

tableau10 = [
    "blue",  # 0
    "darkorange",  # 1
    "green",  # 2
    "crimson",  # 3
    "mediumpurple",  # 4
    "saddlebrown",  # 5
    "orchid",  # 6
    "gray",  # 7
    "olive",  # 8
    "mediumturquoise",  # 9
]

tableau10_light = [
    "lightsteelblue",  # 0
    "peachpuff",  # 1
    "lightgreen",  # 2
    "lightcoral",  # 3
    "thistle",  # 4
    "rosybrown",  # 5
    "lightpink",  # 6
    "lightgray",  # 7
    "palegoldenrod",  # 8
    "paleturquoise",  # 9
]

tab10_index = [3, 0, 2, 1, 2, 4, 5, 6, 7, 8, 9]

# Modern index: direct sequential access (no remapping)
modern_index = list(range(10))


class PlotScheme(object):
    def __init__(self):
        # to have a tight packing on the chart whether only the x axis or also
        # the y axis have (see matplotlib)
        self.ytight = False

        # y-margin (top/bottom) for the subcharts. This will not overrule the
        # option plotinfo.plotymargin
        self.yadjust = 0.0
        # Each new line is in z-order below the previous one. change it False
        # to have lines paint above the previous line
        self.zdown = True
        # Rotation of the date labels on the x axis
        self.tickrotation = 15

        # How many "subparts" takes a major chart (datas) in the overall chart
        # This is proportional to the total number of subcharts
        self.rowsmajor = 5

        # How many "subparts" takes a minor chart (indicators/observers) in the
        # overall chart. This is proportional to the total number of subcharts
        # Together with rowsmajor, this defines a proportion ratio between data
        # charts and indicators/observers charts
        self.rowsminor = 1

        # Distance in between subcharts
        self.plotdist = 0.0

        # Have a grid in the background of all charts
        self.grid = True

        # Grid styling
        self.gridcolor = "#e6e6e6"
        self.gridstyle = "-"
        self.gridwidth = 0.6
        self.gridalpha = 0.8

        # Default plotstyle for the OHLC bars which (line -> line on close)
        # Other options: 'bar' and 'candle'
        self.style = "line"

        # Default color for the 'line on close' plot
        self.loc = "#1f77b4"
        # Default color for a bullish bar/candle
        self.barup = "#26a69a"
        # Default color for a bearish bar/candle
        self.bardown = "#ef5350"
        # Level of transparency to apply to bars/candles (NOT USED)
        self.bartrans = 1.0

        # Whether the candlesticks have to be filled or be transparent
        self.barupfill = True
        self.bardownfill = True

        # Opacity for the filled candlesticks (1.0 opaque - 0.0 transparent)
        self.baralpha = 0.92

        # Alpha blending for fill areas between lines (_fill_gt and _fill_lt)
        self.fillalpha = 0.20

        # Whether to plot volume or not. Note: if the data in question has no
        # volume values, volume plotting will be skipped even if this is True
        self.volume = True

        # Whether to overlay the volume on the data or use a separate subchart
        self.voloverlay = True
        # Scaling of the volume to the data when plotting as overlay
        self.volscaling = 0.33
        # Pushing overlay volume up for better visibility. Experimentation
        # needed if the volume and data overlap too much
        self.volpushup = 0.00

        # Default colour for the volume of a bullish day
        self.volup = "#c8e6c9"
        # Default colour for the volume of a bearish day
        self.voldown = "#ffcdd2"
        # Transparency to apply to the volume when overlaying
        self.voltrans = 0.60

        # Transparency for text labels (NOT USED CURRENTLY)
        self.subtxttrans = 0.66
        # Default font text size for labels on the chart
        self.subtxtsize = 9

        # Transparency for the legend (NOT USED CURRENTLY)
        self.legendtrans = 0.25
        # Whether indicators have a legend display in their charts
        self.legendind = True
        # Location of the legend for indicators (see matplotlib)
        self.legendindloc = "upper left"

        # Location of the legend for datafeeds (see matplotlib)
        self.legenddataloc = "upper left"

        # Plot the last value of a line after the Object name
        self.linevalues = True

        # Plot a tag at the end of each line with the last value
        self.valuetags = True

        # Default color for horizontal lines (see plotinfo.plothlines)
        self.hlinescolor = "#b0b0b0"
        # Default style for horizontal lines
        self.hlinesstyle = "--"
        # Default width for horizontal lines
        self.hlineswidth = 0.8

        # Default color scheme: modern palette
        self.lcolors = modern10

        # Color index mapping
        self._color_index = modern_index

        # strftime Format string for the display of ticks on the x axis
        self.fmt_x_ticks = "%Y-%m-%d %H:%M"

        # strftime Format string for the display of data points values
        self.fmt_x_data = None

        # --- Legend styling ---
        self.legend_frameon = False
        self.legend_framealpha = 0.7
        self.legend_fancybox = True
        self.legend_shadow = False
        self.legend_fontsize = 8

        # --- Figure background ---
        self.facecolor = "#fafafa"
        self.edgecolor = "#fafafa"

        # --- Axis spine styling ---
        self.spines_left = False
        self.spines_top = False
        self.spines_bottom = True
        self.spines_right = True
        self.spine_color = "#cccccc"

        # --- Cursor styling ---
        self.cursor_color = "#555555"
        self.cursor_width = 0.8
        self.cursor_style = ":"

    def color(self, idx):
        colidx = self._color_index[idx % len(self._color_index)]
        return self.lcolors[colidx]
