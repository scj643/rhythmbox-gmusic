# Rhythmbox Google Play Music Plugin

Plugin for playing music from Google Play Music in Rhythmbox 3.x.

## Requirements

* Python 3
* Rhythmbox 3.x
* `gmusicapi`
* Secret storage implementing the [Secret Service DBus API](https://specifications.freedesktop.org/secret-service/)
	* Tested only with `gnome-keyring`

You must have previously logged in to Google Play Music on an Android device.
If you don't have an Android device, you can use Google's official Android
emulator (bundled as part of
[Android Studio](https://developer.android.com/studio/)) to log in to
Google Play Music.

## Installation

First install package dependencies.

### Debian-like distros

	sudo apt-get install make rhythmbox python3-pip gir1.2-glib-2.0 \
		gir1.2-gtk-3.0 gir1.2-rb-3.0 git1.2-peas-1.0 gir1.2-secret-1

### Fedora

	sudo dnf install make rhythmbox python3-pip gobject-introspection \
		gtk3 libsecret libpeas

### Arch

	sudo pacman -S make rhythmbox python-pip gtk3 libpeas libsecret \
		gobject-introspection-runtime

### General Dependencies

Install `gmusicapi` from `pip`:

	sudo pip3 install gmusicapi

### Plugin

Install the plugin for all users:

	sudo make PREFIX=/usr

Install the plugin for just the current user:

	make PREFIX=${HOME}/.local
