from beets import autotag, ui
#from beets.mediafile import MediaFile, FileTypeError, UnreadableFileError
from beets.plugins import BeetsPlugin
from beets.ui import print_, Subcommand


import pygst
pygst.require('0.10')
import gst

from collections import defaultdict
from rgain import rgio
from rgain.script.replaygain import do_gain

import os, logging

log = logging.getLogger('beets')
log.addHandler(logging.StreamHandler())


DEFAULT_REFERENCE_LOUDNESS = 89
DEFAULT_MP3_FORMAT = 'fb2k'
DEFAULT_NO_ALBUM = False


class ReplayGainPlugin(BeetsPlugin):
	'''Provides replay gain analysis for beets'''

	def __init__(self):
		self.register_listener('loaded', self.loaded)
		self.register_listener('album_imported', self.album_imported)

	def configure(self, config):
		self.ref_level =ui.config_val(config, 'replaygain', 'reference_loundess', DEFAULT_REFERENCE_LOUDNESS, int)
		self.mp3_format = ui.config_val(config, 'replaygain', 'mp3_format', DEFAULT_MP3_FORMAT)
		#self.no_album = ui.config_val(config, 'replaygain', 'no_album', DEFAULT_NO_ALBUM, bool)

	def loaded(self):
		pass

	def album_imported(self, album):
		force = True
		dry_run = False
		ignore_cache = False
		is_album = True

		item_paths = [item.path for item in album.items()]

		do_gain(item_paths, self.ref_level, force, dry_run, is_album, self.mp3_format )

