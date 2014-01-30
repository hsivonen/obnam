sources = $(wildcard *.mdwn)

all: manual.pdf manual.html

manual.pdf: Makefile $(sources)
	pandoc --toc --chapters -o manual.pdf $(sources)

manual.html: Makefile $(sources)
	pandoc --toc --chapters --standalone -o manual.html $(sources)

clean:
	rm -f manual.pdf manual.html
