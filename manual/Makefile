TITLE = Backups with Obnam
AUTHOR = Lars Wirzenius (liw@liw.fi)
VERSION = Version $(shell git describe)

sources = $(wildcard *.mdwn)
outputs = manual.pdf manual.html

all: $(outputs)

manual.pdf: Makefile 000.mdwn $(sources)
	pandoc --smart --toc --chapters --number-sections \
		-o manual.pdf $(sources)

manual.html: Makefile 000.mdwn $(sources)
	pandoc  -H manual.css --smart --toc --chapters --number-sections \
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
