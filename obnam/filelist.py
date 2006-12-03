import os


import obnam


def create_file_component(pathname, contref, sigref):
    """Create a FILE component for a given pathname (and metadata)"""
    return create_file_component_from_stat(pathname, os.lstat(pathname), 
                                           contref, sigref)


def create_file_component_from_stat(pathname, st, contref, sigref):
    """Create a FILE component given pathname, stat results, etc"""
    subs = []
    
    c = obnam.cmp.create(obnam.cmp.FILENAME, pathname)
    subs.append(c)
    
    st = obnam.obj.normalize_stat_result(st)

    items = (
        (obnam.cmp.ST_MODE, "st_mode"),
        (obnam.cmp.ST_INO, "st_ino"),
        (obnam.cmp.ST_DEV, "st_dev"),
        (obnam.cmp.ST_NLINK, "st_nlink"),
        (obnam.cmp.ST_UID, "st_uid"),
        (obnam.cmp.ST_GID, "st_gid"),
        (obnam.cmp.ST_SIZE, "st_size"),
        (obnam.cmp.ST_ATIME, "st_atime"),
        (obnam.cmp.ST_MTIME, "st_mtime"),
        (obnam.cmp.ST_CTIME, "st_ctime"),
        (obnam.cmp.ST_BLOCKS, "st_blocks"),
        (obnam.cmp.ST_BLKSIZE, "st_blksize"),
        (obnam.cmp.ST_RDEV, "st_rdev"),
    )
    for kind, key in items:
        if key in st:
            n = obnam.varint.encode(st[key])
            subs.append(obnam.cmp.create(kind, n))

    if contref:
        subs.append(obnam.cmp.create(obnam.cmp.CONTREF, contref))
    if sigref:
        subs.append(obnam.cmp.create(obnam.cmp.SIGREF, sigref))

    return obnam.cmp.create(obnam.cmp.FILE, subs)


def create():
    """Create a new, empty file list"""
    return {}


def num_files(fl):
    """Return the number of files in a file list"""
    return len(fl)


def add(fl, pathname, contref, sigref):
    """Add a file (and its metadata) to a file list"""
    fl[pathname] = create_file_component(pathname, contref, sigref)


def add_file_component(fl, pathname, file_cmp):
    """Add a file component to a file list"""
    fl[pathname] = file_cmp


def find(fl, pathname):
    """Get the FILE component that corresponds to a pathname"""
    return fl.get(pathname, None)


def find_matching_inode(fl, pathname, stat_result):
    """Find the FILE component that matches stat_result"""
    prev = find(fl, pathname)
    if prev:
        prev_subs = obnam.cmp.get_subcomponents(prev)
        nst = obnam.obj.normalize_stat_result(stat_result)
        fields = (
            ("st_dev", obnam.cmp.ST_DEV),
            ("st_ino", obnam.cmp.ST_INO),
            ("st_mode", obnam.cmp.ST_MODE),
            ("st_nlink", obnam.cmp.ST_NLINK),
            ("st_uid", obnam.cmp.ST_UID),
            ("st_gid", obnam.cmp.ST_GID),
            ("st_rdev", obnam.cmp.ST_RDEV),
            ("st_size", obnam.cmp.ST_SIZE),
            ("st_blksize", obnam.cmp.ST_BLKSIZE),
            ("st_blocks", obnam.cmp.ST_BLOCKS),
            ("st_mtime", obnam.cmp.ST_MTIME),
            # No atime or ctime, on purpose. They can be changed without
            # requiring a new backup.
        )
        for a, b in fields:
            b_value = obnam.cmp.first_varint_by_kind(prev_subs, b)
            if nst[a] != b_value:
                return None
        return prev
    else:
        return None


def to_object(fl, object_id):
    """Create an unencoded FILELIST object from a file list"""
    o = obnam.obj.create(object_id, obnam.obj.FILELIST)
    for pathname in fl:
        obnam.obj.add(o, fl[pathname])
    return o


def from_object(o):
    """Create a file list data structure from a backup object"""
    fl = create()
    for file in obnam.obj.find_by_kind(o, obnam.cmp.FILE):
        subs = obnam.cmp.get_subcomponents(file)
        pathname = obnam.cmp.first_string_by_kind(subs, 
                        obnam.cmp.FILENAME)
        fl[pathname] = file
    return fl
