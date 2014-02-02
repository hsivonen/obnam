sources = $(wildcard *.mdwn)
outputs = manual.pdf manual.html

all: $(outputs)

manual.pdf: Makefile $(sources)
	pandoc --toc --chapters -o manual.pdf $(sources)

manual.html: Makefile $(sources)
	pandoc -H manual.css --toc --chapters --standalone \
		-o manual.html $(sources)

clean:
	rm -f manual.pdf manual.html

publish: $(outputs)
	rsync $(outputs) code.liw.fi:code.liw.fi/obnam/manual/.
