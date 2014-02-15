TITLE = Backups with Obnam
AUTHOR = Lars Wirzenius (liw@liw.fi)
VERSION = Version $(shell git describe)

sources = 000.mdwn $(shell ls *.mdwn | grep -vFx 000.mdwn)
outputs = manual.pdf manual.html

all: $(outputs)

manual.pdf: Makefile $(sources)
	pandoc --smart --toc --chapters --number-sections \
		-o manual.pdf $(sources)

manual.html: Makefile $(sources) ../obnam.css
	pandoc  -H ../obnam.css --smart --toc --chapters --number-sections \
		--standalone \
                --self-contained \
		-o manual.html $(sources)

000.mdwn:
	(echo "% $(TITLE)"; echo "% $(AUTHOR)"; echo "% $(VERSION)") \
		> 000.mdwn

clean:
	rm -f $(outputs) 000.mdwn

publish: $(outputs)
	rsync $(outputs) code.liw.fi:code.liw.fi/obnam/manual/.
