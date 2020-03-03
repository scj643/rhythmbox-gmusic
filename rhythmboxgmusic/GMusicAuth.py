# vim: syntax=python:ts=4:sts=4:expandtab:tw=80
import gettext
import json
import os
from oauth2client.client import OAuth2Credentials

from gi import require_version

require_version("Gtk", "3.0")
require_version("Secret", "1")

from gettext import lgettext as _
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Secret
from gmusicapi import Mobileclient
from gmusicapi.session import Mobileclient as SessionMobileClient
from xdg import BaseDirectory

from typing import List, Optional

APP_KEY = "rhythmbox-gmusic"

gettext.bindtextdomain(APP_KEY, "/usr/share/locale")
gettext.textdomain(APP_KEY)

SCHEMA = Secret.Schema.new(
    "rhythmbox.gmusic.credentials",
    Secret.SchemaFlags.NONE,
    {"id": Secret.SchemaAttributeType.STRING,
     "kind": Secret.SchemaAttributeType.STRING},
)
# We are using kind since we want to store auth data and device id in the keychain
attrs = {"id": APP_KEY}
session = Mobileclient(False)


def get_credentials():
    """
    Get stored device id and oauth credentials
    :return:
    """
    try:
        device_id = Secret.password_lookup_sync(SCHEMA, {"kind": "device", **attrs}, None)
        oauth = Secret.password_lookup_sync(SCHEMA, {"kind": "oauth", **attrs}, None)
        if oauth is not None:
            if device_id is None:
                device_id = '""'

            return device_id, OAuth2Credentials.from_json(oauth)
    except GLib.Error:
        session.logger.exception("Failed to retrieve secret from the keyring")
        return None, None
    session.logger.warning("No credential found in the keying")
    return None, None


def set_credentials(oauth_token: OAuth2Credentials) -> None:
    Secret.password_store_sync(
        SCHEMA,
        {"kind": "oauth", **attrs},
        Secret.COLLECTION_DEFAULT,
        APP_KEY,
        oauth_token.to_json(),
        None,
    )


def save_device_id(device_id: str) -> None:
    if not Secret.password_lookup_sync(SCHEMA, {"kind": "device", **attrs}, None):
        Secret.password_store_sync(SCHEMA, {"kind": "device", **attrs}, Secret.COLLECTION_DEFAULT, APP_KEY, device_id,
                                   None)


def gmusic_login() -> bool:
    if session.is_authenticated():
        session.logger.warning("is_authenticated")
        return True

    device_id, oauth = get_credentials()
    if oauth is None:
        return False

    return session.oauth_login(device_id, oauth)


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
            _("Please enter your Google Auth token").decode("UTF-8")
        )
        password_label = Gtk.Label(_("Oauth Token:").decode("UTF-8"))
        self.password_input = Gtk.Entry()
        self.password_input.set_visibility(False)
        password_box = Gtk.HBox()
        password_box.add(password_label)
        password_box.add(self.password_input)
        vbox = Gtk.VBox()
        vbox.add(top_label)
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
