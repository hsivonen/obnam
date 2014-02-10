sources = $(wildcard *.mdwn)
outputs = manual.pdf manual.html

all: $(outputs)

manual.pdf: Makefile $(sources)
	pandoc --smart --toc --chapters --number-sections \
		-o manual.pdf $(sources)

manual.html: Makefile $(sources)
	pandoc  -H manual.css --smart --toc --chapters --number-sections \
		--standalone \
                --self-contained \
		-o manual.html $(sources)

clean:
	rm -f manual.pdf manual.html

publish: $(outputs)
	rsync $(outputs) code.liw.fi:code.liw.fi/obnam/manual/.
