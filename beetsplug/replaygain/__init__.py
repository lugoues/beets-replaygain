#Copyright (c) 2011, Peter Brunner (Lugoues)
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

#portions of this plugin was borred from the rgain package 
#http://pypi.python.org/pypi/rgain/1.0.1

from beets import autotag, ui
from beets.plugins import BeetsPlugin
from beets.ui import print_, Subcommand

import sys
import os.path
import gobject

import pygst
pygst.require('0.10')
import gst

from rgain import rgio
from rgain.script import ou, un, Error, common_options


from collections import defaultdict
from rgain import rgio
#from rgain.script.replaygain import do_gain

import os, logging

log = logging.getLogger('beets')
log.addHandler(logging.StreamHandler())


DEFAULT_REFERENCE_LOUDNESS = 89
DEFAULT_MP3_FORMAT = 'fb2k'
DEFAULT_NO_ALBUM = False

verbose = False

class ReplayGainPlugin(BeetsPlugin):
    '''Provides replay gain analysis for beets'''

    def __init__(self):
        self.register_listener('album_imported', self.album_imported)

    def configure(self, config):
        self.ref_level =ui.config_val(config, 'replaygain', 'reference_loundess', DEFAULT_REFERENCE_LOUDNESS, int)
        self.mp3_format = ui.config_val(config, 'replaygain', 'mp3_format', DEFAULT_MP3_FORMAT)
        #self.no_album = ui.config_val(config, 'replaygain', 'no_album', DEFAULT_NO_ALBUM, bool)
    
    def album_imported(self, album):
        force = True
        dry_run = False        
        is_album = True
        verbose = False
        
        print_("Tagging Replay Gain:  %s - %s" % (album.albumartist, album.album))
        
        item_paths = [item.path for item in album.items()]
        do_gain(item_paths, self.ref_level, force, dry_run, is_album, self.mp3_format )

# calculate the gain for the given files
def calculate_gain(files, ref_level):
    # this has to be done here since Gstreamer hooks into the command line
    # arguments if it's imported on module level
    from rgain import rgcalc

    # handlers
    def on_finished(evsrc, trackdata, albumdata):
        loop.quit()

    def on_trk_started(evsrc, filename):
        if verbose: print_( ou("  %s:" % filename.decode("utf-8")))

    def on_trk_finished(evsrc, filename, gaindata):
        if gaindata:
            if verbose: print_( "%.2f dB" % gaindata.gain)
        else:
            if verbose: print_( "done" )

    rg = rgcalc.ReplayGain(files, True, ref_level)
    rg.connect("all-finished", on_finished)
    rg.connect("track-started", on_trk_started)
    rg.connect("track-finished", on_trk_finished)
    loop = gobject.MainLoop()
    rg.start()
    loop.run()
    return rg.track_data, rg.album_data


def do_gain(files, ref_level=89, force=False, dry_run=False, album=True,
            mp3_format="ql"):
    
    files = [un(filename, sys.getfilesystemencoding()) for filename in files]
    
    formats_map = rgio.BaseFormatsMap(mp3_format)
    
    newfiles = []
    for filename in files:
        if not os.path.splitext(filename)[1] in formats_map.supported_formats:
            if verbose: print_( ou(u"%s: not supported, ignoring it" % filename))
        else:
            newfiles.append(filename)
    files = newfiles
    
    if not force:
        if verbose: print_( "Checking for Replay Gain information ...")
        newfiles = []
        for filename in files:
            if verbose: print_( ou(u"  %s:" % filename))
            try:
                trackdata, albumdata = formats_map.read_gain(filename)
            except Exception, exc:
                raise Error(u"%s: error - %s" % (filename, exc))
            else:
                if trackdata and albumdata:
                    if verbose: print_( "track and album")
                elif not trackdata and albumdata:
                    if verbose: print_( "album only")
                    newfiles.append(filename)
                elif trackdata and not albumdata:
                    if verbose: print_( "track only")
                    if album:
                        newfiles.append(filename)
                else:
                    if verbose: print_( "none")
                    newfiles.append(filename)
        
        if not album:
            files = newfiles
        elif not len(newfiles):
            files = newfiles
    
    if not files:
        # no files left
        if verbose: print_( "Nothing to do.")
        return 0
    
    # calculate gain
    if verbose: print_( "Calculating Replay Gain information ...")
    try:
        tracks_data, albumdata = calculate_gain(files, ref_level)
        if album:
            if verbose: print_( "  Album gain: %.2f dB" % albumdata.gain)
    except Exception, exc:
        raise Error(u"Error while calculating gain - %s" % exc)
    
    if not album:
        albumdata = None
    
    # write gain
    if not dry_run:
        if verbose: print_( "Writing Replay Gain information to files ...")
        for filename, trackdata in tracks_data.iteritems():
            if verbose: print_( ou(u"  %s:" % filename))
            try:
                formats_map.write_gain(filename, trackdata, albumdata)
            except Exception, exc:
                raise Error(u"%s: error - %s" % (filename, exc))
            else:
                if verbose: print_( "done")
    
    if verbose: print_( "Done" )