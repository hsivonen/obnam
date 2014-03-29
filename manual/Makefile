TITLE_EN = Backups with Obnam
AUTHOR = Lars Wirzenius (liw@liw.fi)
VERSION = Version $(shell git describe)

en_sources = $(shell ls en/*.mdwn)
outputs = obnam-manual.en.pdf obnam-manual.en.html

all: $(outputs)

obnam-manual.en.pdf: Makefile $(en_sources)
	./format-pdf $@ "$(TITLE_EN)" "$(AUTHOR)" "$(VERSION)" $(en_sources)

obnam-manual.en.html: Makefile $(en_sources) ../obnam.css
	./format-html $@ "$(TITLE_EN)" "$(AUTHOR)" "$(VERSION)" $(en_sources)

clean:
	rm -f $(outputs) en/000.mdwn
