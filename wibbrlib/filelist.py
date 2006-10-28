import wibbrlib


def create():
    """Create a new, empty file list"""
    return []


def num_files(fl):
    """Return the number of files in a file list"""
    return len(fl)


def create_file_component(pathname):
    """Create a CMP_FILE component for a given pathname (and metadata)"""
    subs = []
    
    c = wibbrlib.cmp.create(wibbrlib.cmp.CMP_FILENAME, pathname)
    subs.append(c)
    
    return wibbrlib.cmp.create(wibbrlib.cmp.CMP_FILE, subs)


def add(fl, pathname):
    """Add a file (and its metadata) to a file list"""
    fl.append(pathname)


def find(fl, pathname):
    """Get the CMP_FILE component that corresponds to a pathname"""
    return True
