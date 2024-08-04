# use system packages until ueberzug is available on pip again
# https://github.com/ueber-devel/ueberzug/issues/20#issuecomment-2261124073
.PHONY: install
install:
	pipx install --force --system-site-packages .
