PYTHON = python

prefix = /usr/local
bindir = $(prefix)/bin

all: _obnam.so obnam.1 obnam-benchmark.1

_obnam.so: _obnammodule.c
	if $(PYTHON) setup.py build > setup.log 2>&1; then \
            rm setup.log; else cat setup.log; exit 1; fi
	cp build/lib*/*.so .
	rm -rf build

obnam.1: obnam.1.in
	./obnam --generate-manpage=obnam.1.in > obnam.1

obnam-benchmark.1: obnam-benchmark.1.in obnam-benchmark
	./obnam-benchmark --generate-manpage=obnam-benchmark.1.in \
		> obnam-benchmark.1

fast-check:
	python -m CoverageTestRunner --ignore-missing-from=without-tests
	rm .coverage

check: fast-check
	python blackboxtest
	
clean:
	rm -f _obnam.so obnamlib/*.pyc obnamlib/plugins/*.pyc test-plugins/*.pyc
	rm -f blackboxtest.log blackboxtest-obnam.log obnam.prof obnam.1
	rm -f obnam-benchmark.1
	rm -rf build
