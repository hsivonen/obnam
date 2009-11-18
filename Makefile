all:

check:
	python -m CoverageTestRunner --ignore-missing-from=without-tests
	rm .coverage
