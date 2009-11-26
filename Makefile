PYTHON = python

all: _obnam.so

_obnam.so: _obnammodule.c
	if $(PYTHON) setup.py build > setup.log 2>&1; then \
            rm setup.log; else cat setup.log; exit 1; fi
	cp build/lib*/*.so .
	rm -rf build

check: all
	python -m CoverageTestRunner --ignore-missing-from=without-tests
	rm .coverage
	
clean:
	rm -f _obnam.so obnamlib/*.pyc

