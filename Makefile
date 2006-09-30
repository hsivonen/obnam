all:


check:
	python testrun.py


clean:
	rm -rf *~ *.pyc *.pyo wibbrlib/*.pyc wibbrlib/*.pyo tmp.*
