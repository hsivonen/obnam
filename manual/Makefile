TITLE_EN = Backups with Obnam
TITLE_DE = Backups mit Obnam
TRANS_DE = Übersetzung: Jan Niggemann (jn@hz6.de)
AUTHOR = Lars Wirzenius (liw@liw.fi)
VERSION = Version $(shell git describe)

en_sources = $(shell ls en/*.mdwn)
de_sources = $(shell ls de/*.mdwn)
outputs = obnam-manual.en.pdf obnam-manual.en.html obnam-manual.de.pdf obnam-manual.de.html

all: $(outputs)

obnam-manual.en.pdf: Makefile $(en_sources)
	./format-pdf $@ "$(TITLE_EN)" "$(AUTHOR)" "$(VERSION)" $(en_sources)

obnam-manual.en.html: Makefile $(en_sources) ../obnam.css
	./format-html $@ "$(TITLE_EN)" "$(AUTHOR)" "$(VERSION)" $(en_sources)

obnam-manual.de.pdf: Makefile $(de_sources)
	./format-de-pdf $@ "$(TITLE_DE)" "$(AUTHOR)" "$(VERSION)" "$(TRANS_DE)" $(de_sources)

obnam-manual.de.html: Makefile $(de_sources) ../obnam.css
	./format-de-html $@ "$(TITLE_DE)" "$(AUTHOR)" "$(VERSION)" "$(TRANS_DE)" $(de_sources)

clean:
	rm -f $(outputs) en/000.mdwn
	rm -f $(outputs) de/000.mdwn
