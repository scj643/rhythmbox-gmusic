# vim: syntax=python:ts=4:sts=4:expandtab:tw=80
import gettext
import json
import os

from gi import require_version

require_version("Gtk", "3.0")
require_version("Secret", "1")

from gettext import lgettext as _
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Secret
from gmusicapi import Mobileclient
from xdg import BaseDirectory

from typing import List

APP_KEY = "rhythmbox-gmusic"

gettext.bindtextdomain(APP_KEY, "/usr/share/locale")
gettext.textdomain(APP_KEY)

SCHEMA = Secret.Schema.new(
    "rhythmbox.gmusic.credentials",
    Secret.SchemaFlags.NONE,
    {"id": Secret.SchemaAttributeType.STRING},
)
attrs = {"id": APP_KEY}
session = Mobileclient(False)
device_id_file = os.path.join(
    BaseDirectory.xdg_config_home, APP_KEY, "device_id"
)


def get_credentials() -> List[str]:
    try:
        credential = Secret.password_lookup_sync(SCHEMA, attrs, None)
        if credential is not None:
            return json.loads(credential)
    except GLib.Error:
        session.logger.exception("Failed to retrieve secret from the keyring")
        return [None, None]
    session.logger.warning("No credential found in the keying")
    return [None, None]


def set_credentials(username: str, password: str) -> None:
    Secret.password_store_sync(
        SCHEMA,
        attrs,
        Secret.COLLECTION_DEFAULT,
        APP_KEY,
        json.dumps([username, password]),
        None,
    )


def get_device_id() -> str:
    if not os.path.isfile(device_id_file):
        return None
    with open(device_id_file) as f:
        return f.read().strip()


def save_device_id(device_id: str) -> None:
    if not os.path.exists(device_id_file):
        os.makedirs(os.path.dirname(device_id_file), mode=0o700, exist_ok=True)

    with open(device_id_file, "w") as f:
        f.write(device_id.strip())


def gmusic_login() -> bool:
    if session.is_authenticated():
        session.logger.warning("is_authenticated")
        return True

    login, password = get_credentials()
    if login is None or password is None:
        return False

    device_id = get_device_id()
    if device_id is None or device_id == "":
        # Force an exception, which is expected to be caught and dealt with
        device_id = "0123456789abcdef"

    return session.login(login, password, device_id)


class AuthDialog(Gtk.Dialog):
    def __init__(self) -> None:
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


class DeviceIdDialog(Gtk.Dialog):
    def __init__(self, device_ids: List[str]) -> None:
        Gtk.Dialog.__init__(
            self,
            _("Choose a device ID").decode("UTF-8"),
            None,
            0,
            (
                Gtk.STOCK_CANCEL,
                Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OK,
                Gtk.ResponseType.OK,
            ),
        )

        top_label = Gtk.Label(_("Choose a device ID").decode("UTF-8"))
        device_id_label = Gtk.Label(_("Device ID:").decode("UTF-8"))
        device_id_store = Gtk.ListStore(str)
        for i in sorted(device_ids):
            device_id_store.append([i])
        self.device_id = Gtk.ComboBox.new_with_model(device_id_store)
        renderer_text = Gtk.CellRendererText()
        self.device_id.pack_start(renderer_text, True)
        self.device_id.add_attribute(renderer_text, "text", 0)

        device_id_box = Gtk.HBox()
        device_id_box.add(device_id_label)
        device_id_box.add(self.device_id)

        vbox = Gtk.VBox()

        vbox.add(top_label)
        vbox.add(device_id_box)

        box = self.get_content_area()
        box.add(vbox)

        self.show_all()
