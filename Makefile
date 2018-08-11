NAME ?= rhythmbox-gmusic
MODNAME = rhythmboxgmusic
VERSION ?= 4.0
PREFIX ?= /usr/local
DESTDIR ?=

ifneq ($(wildcard $(PREFIX)/lib64/rhythmbox),)
# Global 64-bit Rhythmbox on some systems
RHYTHMBOX_BASE := $(DESTDIR)$(PREFIX)/lib64/rhythmbox
else
ifneq ($(wildcard $(PREFIX)/lib/rhythmbox),)
# Global Rhythmbox on some 64-bit and all 32-bit systems
RHYTHMBOX_BASE := $(DESTDIR)$(PREFIX)/lib/rhythmbox
else
ifeq ($(realpath $(PREFIX)),$(realpath $(HOME)/.local))
# If the prefix is the user's local directory
RHYTHMBOX_BASE := $(DESTDIR)$(PREFIX)/share/rhythmbox
else
# No directory available
$(error Rhythmbox directory not found, is it installed?)
endif
endif
endif

define execute
$(1)

endef

install:
	install -d -m 0755 "$(RHYTHMBOX_BASE)/plugins/$(MODNAME)"
	$(foreach f,$(shell find rhythmboxgmusic -type f -not -wholename '*/__pycache__/*'),$(call execute,install -m 0644 "$(f)" "$(RHYTHMBOX_BASE)/plugins/$(f)"))
	install -m 0644 $(MODNAME).plugin "$(RHYTHMBOX_BASE)/plugins/$(MODNAME)/$(MODNAME).plugin"
	python3 -m compileall "$(RHYTHMBOX_BASE)/plugins/$(MODNAME)"
	$(foreach l,$(shell find po/ -mindepth 1 -maxdepth 1 -type d | xargs basename),$(call execute,install -D -m 0644 "po/$(l)/rhythmbox-gmusic.po" "$(DESTDIR)$(PREFIX)/share/locale/$(l)/rhythmbox-gmusic.po"))
