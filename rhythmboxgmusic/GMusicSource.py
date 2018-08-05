# vim: syntax=python:ts=4:sts=4:expandtab:tw=80
import gettext
import GMusicAuth

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

gettext.bindtextdomain("rhythmbox-gmusic", "/usr/share/locale")
gettext.textdomain("rhythmbox-gmusic")

executor = futures.ThreadPoolExecutor(max_workers=1)


class GEntry(RB.RhythmDBEntryType):
    def __init__(self):
        RB.RhythmDBEntryType.__init__(self)

    def do_get_playback_uri(self, entry):
        id = entry.dup_string(RB.RhythmDBPropType.LOCATION).split("/")[1]
        return GMusicAuth.session.get_stream_url(id)

    def do_can_sync_metadata(self, entry):
        return True


gentry = GEntry()


class GooglePlayBaseSource(RB.Source):
    def setup(self):
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
        if self.gmusic_login():
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

    def on_search(self, entry, text):
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

    def update_view(self, *args):
        self.songs_view.set_model(self.browser.props.output_model)
        self.props.query_model = self.browser.props.output_model

    def init_authenticated(self):
        if hasattr(self, "auth_box"):
            self.top_box.remove(self.auth_needed_bar)
        self.load_songs()

    def gmusic_login(self):
        if GMusicAuth.session.is_authenticated():
            return True
        login, password = GMusicAuth.get_credentials()
        return GMusicAuth.session.login(
            login, password, "Mapi.FROM_MAC_ADDRESS"
        )

    def auth(self, widget):
        dialog = GMusicAuth.AuthDialog()
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            login = dialog.login_input.get_text()
            password = dialog.password_input.get_text()
            GMusicAuth.set_credentials(login, password)
            if self.gmusic_login():
                self.init_authenticated()
        dialog.destroy()

    def do_impl_get_entry_view(self):
        return self.songs_view

    def create_entry_from_track_data(self, src_id, id_key, track):
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
    def load_songs(self):
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

    def load_playlists(self):
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
    def setup(self, id, trackdata):
        self.id = id
        self.trackdata = trackdata
        GooglePlayBaseSource.setup(self)

    def load_songs(self):
        future = executor.submit(get_playlist_songs, self.id)
        future.add_done_callback(self.init_songs)

    def on_search(self, entry, text):
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

    def init_songs(self, future):
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


def get_playlist_songs(id):
    try:
        # Mobile API can't get a single playlist's contents
        playlists = GMusicAuth.session.get_all_user_playlist_contents()
        for playlist in playlists:
            if playlist["id"] == id:
                return playlist["tracks"]
    except KeyError:
        return []
