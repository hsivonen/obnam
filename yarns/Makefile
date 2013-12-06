yarns = $(shell ls [0-9][0-9][0-9][0-9]-*.yarn)

all: pdf

pdf: $(yarns) Makefile
	pandoc --chapters --toc -o yarns.pdf $(yarns)

clean:
	rm -f yarns.pdf