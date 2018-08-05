# vim: syntax=python:ts=4:sts=4:expandtab:tw=80
import gettext
import json

from gi import require_version

require_version("GnomeKeyring", "1.0")
require_version("Gtk", "3.0")

from gettext import lgettext as _
from gi.repository import Gio
from gi.repository import GnomeKeyring
from gi.repository import Gtk
from gmusicapi import Mobileclient

gettext.bindtextdomain("rhythmbox-gmusic", "/usr/share/locale")
gettext.textdomain("rhythmbox-gmusic")

APP_KEY = "rhythmbox-gmusic"
_result, KEYRING = GnomeKeyring.get_default_keyring_sync()
GnomeKeyring.unlock_sync(KEYRING, None)
session = Mobileclient(False)


def get_credentials():
    attrs = GnomeKeyring.Attribute.list_new()
    GnomeKeyring.Attribute.list_append_string(attrs, "id", APP_KEY)
    result, value = GnomeKeyring.find_items_sync(
        GnomeKeyring.ItemType.GENERIC_SECRET, attrs
    )
    if result == GnomeKeyring.Result.OK:
        return json.loads(value[0].secret)
    else:
        return "", ""


def set_credentials(username, password):
    if KEYRING is not None:
        GnomeKeyring.create_sync(KEYRING, None)
    attrs = GnomeKeyring.Attribute.list_new()
    GnomeKeyring.Attribute.list_append_string(attrs, "id", APP_KEY)
    GnomeKeyring.item_create_sync(
        KEYRING,
        GnomeKeyring.ItemType.GENERIC_SECRET,
        APP_KEY,
        attrs,
        json.dumps([username, password]),
        True,
    )


class AuthDialog(Gtk.Dialog):
    def __init__(self):
        Gtk.Dialog.__init__(
            self,
            _("Your Google account credentials").decode("UTF-8"),
            None,
            0,
            (
                Gtk.STOCK_CANCEL,
                Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OK,
                Gtk.ResponseType.OK,
            ),
        )
        top_label = Gtk.Label(
            _("Please enter your Google account credentials").decode("UTF-8")
        )
        login_label = Gtk.Label(_("Login:").decode("UTF-8"))
        self.login_input = Gtk.Entry()
        login_box = Gtk.HBox()
        login_box.add(login_label)
        login_box.add(self.login_input)
        password_label = Gtk.Label(_("Password:").decode("UTF-8"))
        self.password_input = Gtk.Entry()
        self.password_input.set_visibility(False)
        password_box = Gtk.HBox()
        password_box.add(password_label)
        password_box.add(self.password_input)
        vbox = Gtk.VBox()
        vbox.add(top_label)
        vbox.add(login_box)
        vbox.add(password_box)
        box = self.get_content_area()
        box.add(vbox)
        self.show_all()
