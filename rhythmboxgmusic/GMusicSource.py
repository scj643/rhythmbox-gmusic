# vim: syntax=python:ts=4:sts=4:expandtab:tw=80
import gettext
import webbrowser

import gmusicapi
from oauth2client.client import OAuth2WebServerFlow

try:
    from . import GMusicAuth
except ImportError:
    # noinspection PyUnresolvedReferences
    import GMusicAuth

import os
import re

from gi import require_version

require_version("Gtk", "3.0")
require_version("RB", "3.0")

from concurrent import futures
from gettext import lgettext as _
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import RB
from urllib.request import urlopen
from xdg import BaseDirectory

from typing import Dict
from typing import List

gettext.bindtextdomain("rhythmbox-gmusic", "/usr/share/locale")
gettext.textdomain("rhythmbox-gmusic")

executor = futures.ThreadPoolExecutor(max_workers=1)


class GEntry(RB.RhythmDBEntryType):
    def __init__(self) -> None:
        RB.RhythmDBEntryType.__init__(self)
        self.cache_dir = os.path.join(
            BaseDirectory.xdg_cache_home, GMusicAuth.APP_KEY, "music"
        )
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, mode=0o700, exist_ok=True)

    def do_get_playback_uri(self, entry) -> str:
        id = entry.dup_string(RB.RhythmDBPropType.LOCATION).split("/")[1]
        artist = entry.dup_string(RB.RhythmDBPropType.ARTIST)
        album = entry.dup_string(RB.RhythmDBPropType.ALBUM)
        title = entry.dup_string(RB.RhythmDBPropType.TITLE)
        cache_file = os.path.join(self.cache_dir, artist, album, title)
        if not os.path.isfile(cache_file):
            # Try to download the song for local caching, fall back to the URL
            url = GMusicAuth.session.get_stream_url(id)
            try:
                response = urlopen(url)
                GMusicAuth.session.logger.warning(
                    f"HTTP_CODE:{response.status}"
                )
                GMusicAuth.session.logger.warning(
                    f"HTTP_HEADERS:{response.getheaders()}"
                )
                if not os.path.isdir(os.path.dirname(cache_file)):
                    os.makedirs(
                        os.path.dirname(cache_file), mode=0o700, exist_ok=True
                    )
                with open(cache_file, "bw") as f:
                    f.write(response.read())
            except Exception:
                return url

        return f"file://{cache_file}"

    def do_can_sync_metadata(self, entry) -> bool:
        return True


gentry = GEntry()


class GooglePlayBaseSource(RB.Source):
    def setup(self) -> None:
        shell = self.props.shell
        self.songs_view = RB.EntryView.new(
            db=shell.props.db,
            shell_player=shell.props.shell_player,
            is_drag_source=True,
            is_drag_dest=False,
        )
        self.songs_view.append_column(RB.EntryViewColumn.TRACK_NUMBER, True)
        self.songs_view.append_column(RB.EntryViewColumn.TITLE, True)
        self.songs_view.append_column(RB.EntryViewColumn.ARTIST, True)
        self.songs_view.append_column(RB.EntryViewColumn.ALBUM, True)
        self.songs_view.append_column(RB.EntryViewColumn.DURATION, True)
        self.songs_view.connect(
            "notify::sort-order",
            lambda *args, **kwargs: self.songs_view.resort_model(),
        )
        self.songs_view.connect(
            "entry-activated",
            lambda view, entry: shell.props.shell_player.play_entry(
                entry, self
            ),
        )
        self.vbox = Gtk.Paned.new(Gtk.Orientation.VERTICAL)
        self.top_box = Gtk.VBox()
        is_authed = False
        try:
            is_authed = GMusicAuth.gmusic_login()
        except:
            pass
        if is_authed:
            self.init_authenticated()
        else:
            self.auth_needed_bar = Gtk.InfoBar()
            self.top_box.pack_start(self.auth_needed_bar, True, True, 0)
            self.auth_needed_bar.set_message_type(Gtk.MessageType.INFO)
            auth_btn = self.auth_needed_bar.add_button(
                _("Click here to login").decode("UTF-8"), 1
            )
            auth_btn.connect("clicked", self.auth)
            label = Gtk.Label(
                _(
                    "This plugin requires you to authenticate to Google Play"
                ).decode("UTF-8")
            )
            self.auth_needed_bar.get_content_area().add(label)
        self.browser = RB.LibraryBrowser.new(shell.props.db, gentry)
        self.browser.set_model(self.props.base_query_model, False)
        self.browser.connect("notify::output-model", self.update_view)
        self.browser.set_size_request(-1, 200)

        self.search_widget = RB.SearchEntry.new(False)
        self.search_widget.connect("search", self.on_search)

        search_box = Gtk.Alignment.new(1, 0, 0, 1)
        search_box.add(self.search_widget)

        self.top_box.pack_start(search_box, False, False, 5)
        self.top_box.pack_start(self.browser, True, True, 0)

        self.update_view()

        self.vbox.add1(self.top_box)
        self.vbox.add2(self.songs_view)
        self.pack_start(self.vbox, True, True, 0)
        self.show_all()

    def on_search(self, entry, text: str) -> None:
        db = self.props.shell.props.db
        query_model = RB.RhythmDBQueryModel.new_empty(db)
        query = GLib.PtrArray()
        db.query_append_params(
            query,
            RB.RhythmDBQueryType.FUZZY_MATCH,
            RB.RhythmDBPropType.COMMENT,
            text.lower(),
        )
        db.query_append_params(
            query,
            RB.RhythmDBQueryType.EQUALS,
            RB.RhythmDBPropType.GENRE,
            "google-play-music",  # shit!
        )
        db.do_full_query_parsed(query_model, query)
        self.browser.set_model(query_model, False)
        self.update_view()

    def update_view(self, *args) -> None:
        self.songs_view.set_model(self.browser.props.output_model)
        self.props.query_model = self.browser.props.output_model

    def init_authenticated(self) -> None:
        if hasattr(self, "auth_needed_bar"):
            self.top_box.remove(self.auth_needed_bar)
        self.load_songs()

    def auth(self, widget) -> None:
        device_id, oauth = GMusicAuth.get_credentials()
        if oauth is None:
            flow = OAuth2WebServerFlow(**GMusicAuth.SessionMobileClient.oauth._asdict())
            auth_uri = flow.step1_get_authorize_url()
            webbrowser.open(auth_uri)
            dialog = GMusicAuth.AuthDialog()
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                oauth_text = dialog.password_input.get_text()
                credentials = flow.step2_exchange(oauth_text)
                GMusicAuth.set_credentials(credentials)
            dialog.destroy()

        is_authed = False
        try:
            is_authed = GMusicAuth.gmusic_login()
            GMusicAuth.session.logger.warning("is_authed")
        except gmusicapi.exceptions.InvalidDeviceId as ex:
            registred_device_ids = [
                i for i in ex.valid_device_ids if re.match(r"^[0-9a-f]{16}$", i)
            ]
            if len(registred_device_ids) == 0:
                GMusicAuth.session.logger.error("No valid registered devices!")
                raise

            if len(registred_device_ids) == 1:
                GMusicAuth.save_device_id(registred_device_ids[0])
                is_authed = GMusicAuth.gmusic_login()
            else:
                device_id_dialog = GMusicAuth.DeviceIdDialog(
                    registred_device_ids
                )
                device_id_response = device_id_dialog.run()
                if device_id_response == Gtk.ResponseType.OK:
                    it = device_id_dialog.device_id.get_active_iter()
                    if it is not None:
                        device_id_model = device_id_dialog.device_id.get_model()
                        GMusicAuth.session.logger.error(
                            f"MODEL: {device_id_model[it]}"
                        )
                        GMusicAuth.save_device_id(device_id_model[it][0])
                        is_authed = GMusicAuth.gmusic_login()
                device_id_dialog.destroy()
        if is_authed:
            self.init_authenticated()

    def do_impl_get_entry_view(self) -> RB.EntryView:
        return self.songs_view

    def create_entry_from_track_data(
            self, src_id: str, id_key: str, track: Dict[str, str]
    ) -> RB.RhythmDBEntry:
        shell = self.props.shell
        db = shell.props.db
        entry = RB.RhythmDBEntry.new(db, gentry, src_id + "/" + track[id_key])
        full_title = []
        if "title" in track:
            db.entry_set(entry, RB.RhythmDBPropType.TITLE, track["title"])
            full_title.append(track["title"])
        if "durationMillis" in track:
            db.entry_set(
                entry,
                RB.RhythmDBPropType.DURATION,
                int(track["durationMillis"]) / 1000,
            )
        if "album" in track:
            db.entry_set(entry, RB.RhythmDBPropType.ALBUM, track["album"])
            full_title.append(track["album"])
        if "artist" in track:
            db.entry_set(entry, RB.RhythmDBPropType.ARTIST, track["artist"])
            full_title.append(track["artist"])
        if "trackNumber" in track:
            db.entry_set(
                entry,
                RB.RhythmDBPropType.TRACK_NUMBER,
                int(track["trackNumber"]),
            )
        if "albumArtRef" in track:
            db.entry_set(
                entry,
                RB.RhythmDBPropType.MB_ALBUMID,
                track["albumArtRef"][0]["url"],
            )
        # rhytmbox OR don't work for custom filters
        db.entry_set(
            entry, RB.RhythmDBPropType.COMMENT, " - ".join(full_title).lower()
        )
        # rhythmbox segfoalt when new db created from python
        db.entry_set(entry, RB.RhythmDBPropType.GENRE, "google-play-music")
        return entry

    def load_songs():
        raise NotImplementedError


class GooglePlayLibrary(GooglePlayBaseSource):
    def load_songs(self) -> None:
        shell = self.props.shell
        self.trackdata = GMusicAuth.session.get_all_songs()
        for song in self.trackdata:
            try:
                entry = self.create_entry_from_track_data(
                    getattr(self, "id", "gmusic"), "id", song
                )
                self.props.base_query_model.add_entry(entry, -1)
            except TypeError:  # Already in db
                pass
        shell.props.db.commit()
        self.load_playlists()

    def load_playlists(self) -> None:
        shell = self.props.shell
        db = shell.props.db
        self.playlists = GMusicAuth.session.get_all_playlists()
        for playlist in self.playlists:
            model = RB.RhythmDBQueryModel.new_empty(db)
            pl = GObject.new(
                GooglePlayPlaylist,
                shell=shell,
                name=playlist["name"],
                query_model=model,
                icon=Gio.ThemedIcon.new("playlist"),
            )
            pl.setup(playlist["id"], self.trackdata)
            shell.append_display_page(pl, self)


class GooglePlayPlaylist(GooglePlayBaseSource):
    def setup(self, id: str, trackdata: Dict[str, str]):
        self.id = id
        self.trackdata = trackdata
        GooglePlayBaseSource.setup(self)

    def load_songs(self) -> None:
        future = executor.submit(get_playlist_songs, self.id)
        future.add_done_callback(self.init_songs)

    def on_search(self, entry, text: str) -> None:
        db = self.props.shell.props.db
        query_model = RB.RhythmDBQueryModel.new_empty(db)
        query = GLib.PtrArray()
        db.query_append_params(
            query,
            RB.RhythmDBQueryType.FUZZY_MATCH,
            RB.RhythmDBPropType.COMMENT,
            text.lower(),
        )
        db.query_append_params(
            query,
            RB.RhythmDBQueryType.EQUALS,
            RB.RhythmDBPropType.GENRE,
            "google-play-music-playlist",
        )
        db.do_full_query_parsed(query_model, query)
        self.browser.set_model(query_model, False)
        self.update_view()

    def init_songs(self, future) -> None:
        shell = self.props.shell
        db = shell.props.db
        for track in future.result():
            match = next(
                (td for td in self.trackdata if td["id"] == track["trackId"]),
                None,
            )
            if match:
                entry = self.create_entry_from_track_data(
                    getattr(self, "id", "0"), "id", match
                )
                db.entry_set(
                    entry,
                    RB.RhythmDBPropType.GENRE,
                    "google-play-music-playlist",
                )
                self.props.base_query_model.add_entry(entry, -1)
        db.commit()
        delattr(self, "trackdata")  # Memory concerns


def get_playlist_songs(id: str) -> List[str]:
    try:
        # Mobile API can't get a single playlist's contents
        playlists = GMusicAuth.session.get_all_user_playlist_contents()
        for playlist in playlists:
            if playlist["id"] == id:
                return playlist["tracks"]
    except KeyError:
        return []
