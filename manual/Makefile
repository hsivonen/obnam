TITLE = Backups with Obnam
AUTHOR = Lars Wirzenius (liw@liw.fi)
VERSION = Version $(shell git describe)

en_sources = en/000.mdwn $(shell ls en/*.mdwn | grep -vFx en/000.mdwn)
outputs = obnam-manual.en.pdf obnam-manual.en.html

all: $(outputs)

obnam-manual.en.pdf: Makefile $(en_sources)
	pandoc --smart --toc --chapters --number-sections \
		-o $@ $(en_sources)

obnam-manual.en.html: Makefile $(en_sources) ../obnam.css
	pandoc  -H ../obnam.css --smart --toc --chapters --number-sections \
		--standalone \
                --self-contained \
                -V geometry:lettersize \
		-o $@ $(en_sources)

en/000.mdwn:
	(echo "% $(TITLE)"; echo "% $(AUTHOR)"; echo "% $(VERSION)") \
		> $@

clean:
	rm -f $(outputs) en/000.mdwn
