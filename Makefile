NAME ?= rhythmbox-gmusic
MODNAME = rhythmboxgmusic
VERSION ?= 4.0
PREFIX ?= /usr/local
DESTDIR ?=
RHYTHMBOX_BASE := $(DESTDIR)$(PREFIX)/share/rhythmbox

define execute
$(1)

endef

install:
	install -d -m 0755 "$(RHYTHMBOX_BASE)/plugins/$(MODNAME)"
	$(foreach f,$(shell find rhythmboxgmusic -type f -not -wholename '*/__pycache__/*'),$(call execute,install -m 0644 "$(f)" "$(RHYTHMBOX_BASE)/plugins/$(f)"))
	python3 -m compileall "$(RHYTHMBOX_BASE)/plugins/$(MODNAME)"
	$(foreach l,$(shell find po/ -mindepth 1 -maxdepth 1 -type d | xargs basename),$(call execute,install -D -m 0644 "po/$(l)/rhythmbox-gmusic.po" "$(DESTDIR)$(PREFIX)/share/locale/$(l)/rhythmbox-gmusic.po"))
