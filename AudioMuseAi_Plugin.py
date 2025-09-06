from functools import partial
from urllib.parse import (
    quote,
    urlencode,
)

from PyQt5.QtNetwork import QNetworkRequest

from picard import config, log
from picard.metadata import register_track_metadata_processor
from picard.track import Track
from picard.album import Album
from picard.ui.itemviews import (
    BaseAction,
    register_track_action,
    register_album_action,
)

from PyQt5 import QtWidgets
from picard.ui.options import (
    OptionsPage,
    register_options_page,
)
from picard.config import BoolOption, TextOption

PLUGIN_NAME = "AudioMuse-Ai"
PLUGIN_AUTHOR = "stiv2804"
PLUGIN_DESCRIPTION = (
    "Fetch Music analysis from local AudioMuse-Ai.<br/>"
    ""
)
PLUGIN_VERSION = "1.0.0"
PLUGIN_API_VERSIONS = ["2.0", "2.1", "2.2", "2.3", "2.4", "2.5", "2.6"]
PLUGIN_LICENSE = "MIT"
PLUGIN_LICENSE_URL = "https://opensource.org/licenses/MIT"

audiomuse_search_url = "/external/search"
audiomuse_get_score_url = "/external/get_score"


def _request(ws, url, callback, queryargs=None, important=False):
    if not queryargs:
        queryargs = {}

    ws.get_url(
        url=config.setting["amai_url"]+url,
        handler=callback,
        parse_response_type="json",
        priority=True,
        important=important,
        queryargs=queryargs,
        cacheloadcontrol=QNetworkRequest.PreferCache,
    )


def search_for_AudioData(album, metadata, linked_files):
    artist = metadata["artist"]
    title = metadata["title"]
    if not (artist and title):
        log.debug(
            "{}: artist and title are required to obtain AudioMuse-Ai data".format(
                PLUGIN_NAME
            )
        )
        return

    queryargs = {
        "title": title,
        "artist": artist,
    }
    log.debug(
        "{}: GET {}?{}".format(PLUGIN_NAME, quote(audiomuse_search_url), urlencode(queryargs))
    )
    _request(
        album.tagger.webservice,
        audiomuse_search_url,
        partial(process_search_response, album, metadata, linked_files),
        queryargs,
    )


def process_search_response(album, metadata, linked_files, response, reply, error):

    if error or (not response) or len(response)==0 or not ("item_id" in response[0]):
        album._requests -= 1
        album._finalize_loading(None)
        log.warning(
            '{}: no Audiomuse AI track found for "{}" by {}'.format(
                PLUGIN_NAME, metadata["title"], metadata["artist"]
            )
        )
        return

    log.warning(
            '{}:  found Audiomuse id for "{}" by {} item_id: {}'.format(
                PLUGIN_NAME, metadata["title"], metadata["artist"], response[0]["item_id"]
            )
        )
    album._requests -= 1
    queryargs = {
        "id": response[0]["item_id"]
    }
    log.warning(
        "{}: GET {}?{}".format(PLUGIN_NAME, quote(audiomuse_get_score_url), urlencode(queryargs))
    )
    _request(
        album.tagger.webservice,
        audiomuse_get_score_url,
        partial(process_tag_finding_response, album, metadata, linked_files),
        queryargs,
    )


def set_metadata(metadata, response):
        if("energy" in response):
            metadata["energy"] = response["energy"] 
        if("key" in response):
            metadata["key"] = response["key"] 
        if("scale" in response):
            metadata["scale"] = response["scale"] 
        if("tempo" in response):
            metadata["bpm"] = response["tempo"] 
        

def process_tag_finding_response(album, metadata, linked_files, response, reply, error):

    if error:
        album._requests -= 1
        album._finalize_loading(None)
        log.warning(
            '{}: no Audiomuse AI track found for "{}" by {}'.format(
                PLUGIN_NAME, metadata["title"], metadata["artist"]
            )
        )
        return

    try:
        log.warning(
            '{}:  process_tag_finding_response"{}" by {} {}'.format(
                PLUGIN_NAME, metadata["title"], metadata["artist"], response
            )   
        )
        set_metadata(metadata,response)          
        if linked_files:
            for file in linked_files:
                set_metadata(file.metadata,response)
        log.warning(
            '{}: Audiomuse AI loaded for track "{}" by {}'.format(
                PLUGIN_NAME, metadata["title"], metadata["artist"]
            )
        )

    except (TypeError, KeyError, ValueError):
        log.warn(
            '{}: Audiomuse AI analysis NOT loaded for track "{}" by {}'.format(
                PLUGIN_NAME, metadata["title"], metadata["artist"]
            ),
            exc_info=True,
        )

    finally:
        album._requests -= 1
        album._finalize_loading(None)


class AmailibAnalysisOptionsPage(OptionsPage):

    NAME = "Audiomuse AI"
    TITLE = "Audiomuse AI"
    PARENT = "plugins"

    options = [
            BoolOption("setting", "amai_search_on_load", False),
            TextOption("setting", "amai_url", "http://localhost:8000")
        ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.box = QtWidgets.QVBoxLayout(self)

        self.audiomuse_server_url_label = QtWidgets.QLabel('The Path to the AudioMuse AI API (usually "http://<your AudioMuse Server>:8000")')
        self.box.addWidget(self.audiomuse_server_url_label)

        self.audiomuse_server_url_widget = QtWidgets.QLineEdit("http://<your AudioMuse Server>:8000", self)
        self.box.addWidget(self.audiomuse_server_url_widget)

        #self.search_on_load_widget = QtWidgets.QCheckBox("Search for AudioMuse AI Metadata when loading tracks", self)
        #self.box.addWidget(self.search_on_load_widget)
        

        self.spacer = QtWidgets.QSpacerItem(
            0, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )
        self.box.addItem(self.spacer)

        self.description = QtWidgets.QLabel(self)
        self.description.setText(
            "AudioMuse-AI is an Open Source Dockerized environment that brings Music analysis and\n"
            "smart playlist generation to Jellyfin and Navidrome.\n"
            "This Plugin uses the Analyzed Metadata from AudioMuse-AI into Picard."
        )
        self.description.setOpenExternalLinks(True)
        self.box.addWidget(self.description)

    def load(self):
        #self.search_on_load_widget.setChecked(config.setting["amai_search_on_load"])
        self.audiomuse_server_url_widget.setText(config.setting["amai_url"])

    def save(self):
        #config.setting["amai_search_on_load"] = self.search_on_load_widget.checkState()
        config.setting["amai_url"] = self.audiomuse_server_url_widget.text()


class amailibAnalysisMetadataProcessor:

    def __init__(self):
        super().__init__()

    def process_metadata(self, album, metadata, track, release):
        if config.setting["amai_search_on_load"]:
            search_for_AudioData(album, metadata, None)


class amailibAnalysTrackAction(BaseAction):
    NAME = "Search for metadata from AudioMuse AI..."

    def execute_on_track(self, track):
        search_for_AudioData(track.album, track.metadata, track.linked_files)

    def callback(self, objs):
        for item in (t for t in objs if isinstance(t, Track) or isinstance(t, Album)):
            if isinstance(item, Track):
                log.debug("{}: {}, {}".format(PLUGIN_NAME, item, item.album))
                self.execute_on_track(item)
            elif isinstance(item, Album):
                for track in item.tracks:
                    log.debug("{}: {}, {}".format(PLUGIN_NAME, track, item))
                    self.execute_on_track(track)


register_track_metadata_processor(amailibAnalysisMetadataProcessor().process_metadata)
register_track_action(amailibAnalysTrackAction())
register_album_action(amailibAnalysTrackAction())
register_options_page(AmailibAnalysisOptionsPage)
