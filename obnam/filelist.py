import os


import obnam


def create_file_component(pathname, contref):
    """Create a CMP_FILE component for a given pathname (and metadata)"""
    return create_file_component_from_stat(pathname, os.lstat(pathname), 
                                           contref)


def create_file_component_from_stat(pathname, st, contref):
    """Create a CMP_FILE component given pathname, stat results, etc"""
    subs = []
    
    c = obnam.cmp.create(obnam.cmp.CMP_FILENAME, pathname)
    subs.append(c)
    
    st = obnam.obj.normalize_stat_result(st)

    items = (
        (obnam.cmp.CMP_ST_MODE, "st_mode"),
        (obnam.cmp.CMP_ST_INO, "st_ino"),
        (obnam.cmp.CMP_ST_DEV, "st_dev"),
        (obnam.cmp.CMP_ST_NLINK, "st_nlink"),
        (obnam.cmp.CMP_ST_UID, "st_uid"),
        (obnam.cmp.CMP_ST_GID, "st_gid"),
        (obnam.cmp.CMP_ST_SIZE, "st_size"),
        (obnam.cmp.CMP_ST_ATIME, "st_atime"),
        (obnam.cmp.CMP_ST_MTIME, "st_mtime"),
        (obnam.cmp.CMP_ST_CTIME, "st_ctime"),
        (obnam.cmp.CMP_ST_BLOCKS, "st_blocks"),
        (obnam.cmp.CMP_ST_BLKSIZE, "st_blksize"),
        (obnam.cmp.CMP_ST_RDEV, "st_rdev"),
    )
    for kind, key in items:
        if key in st:
            n = obnam.varint.encode(st[key])
            subs.append(obnam.cmp.create(kind, n))

    if contref:
        subs.append(obnam.cmp.create(obnam.cmp.CMP_CONTREF, contref))

    return obnam.cmp.create(obnam.cmp.CMP_FILE, subs)


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
        prev_subs = obnam.cmp.get_subcomponents(prev)
        nst = obnam.obj.normalize_stat_result(stat_result)
        fields = (
            ("st_dev", obnam.cmp.CMP_ST_DEV),
            ("st_ino", obnam.cmp.CMP_ST_INO),
            ("st_mode", obnam.cmp.CMP_ST_MODE),
            ("st_nlink", obnam.cmp.CMP_ST_NLINK),
            ("st_uid", obnam.cmp.CMP_ST_UID),
            ("st_gid", obnam.cmp.CMP_ST_GID),
            ("st_rdev", obnam.cmp.CMP_ST_RDEV),
            ("st_size", obnam.cmp.CMP_ST_SIZE),
            ("st_blksize", obnam.cmp.CMP_ST_BLKSIZE),
            ("st_blocks", obnam.cmp.CMP_ST_BLOCKS),
            ("st_mtime", obnam.cmp.CMP_ST_MTIME),
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
    """Create an unencoded OBJ_FILELIST object from a file list"""
    o = obnam.obj.create(object_id, obnam.obj.OBJ_FILELIST)
    for pathname in fl:
        obnam.obj.add(o, fl[pathname])
    return o


def from_object(o):
    """Create a file list data structure from a backup object"""
    fl = create()
    for file in obnam.obj.find_by_kind(o, obnam.cmp.CMP_FILE):
        subs = obnam.cmp.get_subcomponents(file)
        pathname = obnam.cmp.first_string_by_kind(subs, 
                        obnam.cmp.CMP_FILENAME)
        fl[pathname] = file
    return fl
