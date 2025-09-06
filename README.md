# MusicBrainzPicard-AudiomuseAi-plugin
This Plugin for [MusicBrainz Picard](https://picard.musicbrainz.org/) connects to a local [Audiomuse Server](https://github.com/NeptuneHub/AudioMuse-AI) and fetches the Metadata into MusicBrainz Picard

## Install
To install this Plugin open MusicBrainz Picard, go to the Settings/Plugins Page. Click "install plugin" and click on the AudioMuseAi_Plugin.py.
Then the Plugin "AudioMuse-AI" should pop up in the Plugins list and click accept.
Activate the Plugin

## Configure
Under "Settings/Plugins/Audiomuse Ai" choose your AudioMuse AI Server URL

## Usage
Make a left click on a Song/Album and choose "Plugins/Search for metadata from AudioMuse AI..."
The Plugin takes always the first item with the Artist and Songname and fetches the metadata "energy", "key", "scale", "tempo".
