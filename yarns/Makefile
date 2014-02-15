yarns = $(shell ls [0-9][0-9][0-9][0-9]-*.yarn)

all: yarns.pdf yarns.html

yarns.pdf: $(yarns) Makefile
	pandoc --chapters --toc -o yarns.pdf $(yarns)

yarns.html: $(yarns) Makefile ../obnam.css
	pandoc -H ../obnam.css --smart --toc --chapters --number-sections \
		--standalone --self-contained -o yarns.html $(yarns)

html:

clean:
	rm -f yarns.pdf