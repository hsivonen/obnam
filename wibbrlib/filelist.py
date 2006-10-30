import os


import wibbrlib


def create_file_component(pathname, contref):
    """Create a CMP_FILE component for a given pathname (and metadata)"""
    subs = []
    
    c = wibbrlib.cmp.create(wibbrlib.cmp.CMP_FILENAME, pathname)
    subs.append(c)
    
    st = os.lstat(pathname)
    st = wibbrlib.obj.normalize_stat_result(st)

    items = (
        (wibbrlib.cmp.CMP_ST_MODE, "st_mode"),
        (wibbrlib.cmp.CMP_ST_INO, "st_ino"),
        (wibbrlib.cmp.CMP_ST_DEV, "st_dev"),
        (wibbrlib.cmp.CMP_ST_NLINK, "st_nlink"),
        (wibbrlib.cmp.CMP_ST_UID, "st_uid"),
        (wibbrlib.cmp.CMP_ST_GID, "st_gid"),
        (wibbrlib.cmp.CMP_ST_SIZE, "st_size"),
        (wibbrlib.cmp.CMP_ST_ATIME, "st_atime"),
        (wibbrlib.cmp.CMP_ST_MTIME, "st_mtime"),
        (wibbrlib.cmp.CMP_ST_CTIME, "st_ctime"),
        (wibbrlib.cmp.CMP_ST_BLOCKS, "st_blocks"),
        (wibbrlib.cmp.CMP_ST_BLKSIZE, "st_blksize"),
        (wibbrlib.cmp.CMP_ST_RDEV, "st_rdev"),
    )
    for kind, key in items:
        if key in st:
            n = wibbrlib.varint.encode(st[key])
            subs.append(wibbrlib.cmp.create(kind, n))

    if contref:
        subs.append(wibbrlib.cmp.create(wibbrlib.cmp.CMP_CONTREF, contref))

    return wibbrlib.cmp.create(wibbrlib.cmp.CMP_FILE, subs)


def create():
    """Create a new, empty file list"""
    return {}


def num_files(fl):
    """Return the number of files in a file list"""
    return len(fl)


def add(fl, pathname, contref):
    """Add a file (and its metadata) to a file list"""
    fl[pathname] = create_file_component(pathname, contref)


def add_file_component(fl, pathname, file_cmp):
    """Add a file component to a file list"""
    fl[pathname] = file_cmp


def find(fl, pathname):
    """Get the CMP_FILE component that corresponds to a pathname"""
    return fl.get(pathname, None)


def find_matching_inode(fl, pathname, stat_result):
    """Find the CMP_FILE component that matches stat_result"""
    prev = find(fl, pathname)
    if prev:
        prev_subs = wibbrlib.cmp.get_subcomponents(prev)
        nst = wibbrlib.obj.normalize_stat_result(stat_result)
        fields = (
            ("st_dev", wibbrlib.cmp.CMP_ST_DEV),
            ("st_ino", wibbrlib.cmp.CMP_ST_INO),
            ("st_mode", wibbrlib.cmp.CMP_ST_MODE),
            ("st_nlink", wibbrlib.cmp.CMP_ST_NLINK),
            ("st_uid", wibbrlib.cmp.CMP_ST_UID),
            ("st_gid", wibbrlib.cmp.CMP_ST_GID),
            ("st_rdev", wibbrlib.cmp.CMP_ST_RDEV),
            ("st_size", wibbrlib.cmp.CMP_ST_SIZE),
            ("st_blksize", wibbrlib.cmp.CMP_ST_BLKSIZE),
            ("st_blocks", wibbrlib.cmp.CMP_ST_BLOCKS),
            ("st_mtime", wibbrlib.cmp.CMP_ST_MTIME),
            # No atime or ctime, on purpose. They can be changed without
            # requiring a new backup.
        )
        for a, b in fields:
            b_value = wibbrlib.cmp.first_varint_by_kind(prev_subs, b)
            if nst[a] != b_value:
                return None
        return prev
    else:
        return None


def to_object(fl, object_id):
    """Create an unencoded OBJ_FILELIST object from a file list"""
    o = wibbrlib.obj.create(object_id, wibbrlib.obj.OBJ_FILELIST)
    for pathname in fl:
        wibbrlib.obj.add(o, fl[pathname])
    return o


def from_object(o):
    """Create a file list data structure from a backup object"""
    fl = create()
    for file in wibbrlib.obj.find_by_kind(o, wibbrlib.cmp.CMP_FILE):
        subs = wibbrlib.cmp.get_subcomponents(file)
        pathname = wibbrlib.cmp.first_string_by_kind(subs, 
                        wibbrlib.cmp.CMP_FILENAME)
        fl[pathname] = file
    return fl
