sources = $(wildcard *.mdwn)

all: manual.pdf manual.html

manual.pdf: $(sources)
	pandoc --toc --chapters -o manual.pdf $(sources)

manual.html: $(sources)
	pandoc --toc --chapters --standalone -o manual.html $(sources)
