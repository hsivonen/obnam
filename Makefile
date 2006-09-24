all:


check:
	python testrun.py


clean:
	rm -f *.pyc *.pyo wibbrlib/*.pyc wibbrlib/*.pyo
