# vim: syntax=python:ts=4:sts=4:expandtab:tw=80
import GMusicSource

from gi import require_version

require_version("Peas", "1.0")
require_version("RB", "3.0")

from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Peas
from gi.repository import RB


class GooglePlayMusic(GObject.Object, Peas.Activatable):
    __gtype_name = "GooglePlayMusicPlugin"
    object = GObject.property(type=GObject.GObject)

    def __init__(self):
        GObject.Object.__init__(self)

    def do_activate(self):
        shell = self.object
        db = shell.props.db
        model = RB.RhythmDBQueryModel.new_empty(db)
        self.source = GObject.new(
            GMusicSource.GooglePlayLibrary,
            shell=shell,
            name="Google Play Music",
            query_model=model,
            plugin=self,
            icon=Gio.ThemedIcon.new("media-playback-start-symbolic"),
        )
        self.source.setup()
        group = RB.DisplayPageGroup.get_by_id("library")
        shell.append_display_page(self.source, group)

    def do_deactivate(self):
        self.source.delete_thyself()
        self.source = None


GObject.type_register(GMusicSource.GooglePlayLibrary)
