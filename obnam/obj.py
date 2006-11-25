import uuid

from obnam.exception import ExceptionBase
import obnam.cmp
import obnam.varint


# Magic cookie at the beginning of every block

BLOCK_COOKIE = "blockhead\n"


# Version of the storage format

FORMAT_VERSION = "1"


# Constants of object kinds

_object_kinds = {}

def _define_kind(code, name):
    assert code not in _object_kinds
    assert name not in _object_kinds.values()
    _object_kinds[code] = name
    return code

OBJ_FILEPART     = _define_kind(1, "OBJ_FILEPART")
OBJ_INODE        = _define_kind(2, "OBJ_INODE")
OBJ_GEN          = _define_kind(3, "OBJ_GEN")
OBJ_SIG          = _define_kind(4, "OBJ_SIG")
OBJ_HOST         = _define_kind(5, "OBJ_HOST")
OBJ_FILECONTENTS = _define_kind(6, "OBJ_FILECONTENTS")
OBJ_FILELIST     = _define_kind(7, "OBJ_FILELIST")


def kind_name(kind):
    """Return a textual name for a numeric object kind"""
    return _object_kinds.get(kind, "OBJ_UNKNOWN")


def object_id_new():
    """Return a string that is a universally unique ID for an object"""
    return str(uuid.uuid4())


class Object:

    def __init__(self):
        self.id = None
        self.kind = None
        self.components = []
        
        
def create(id, kind):
    """Create a new backup object"""
    o = Object()
    o.id = id
    o.kind = kind
    return o


def add(o, c):
    """Add a component to an object"""
    o.components.append(c)


def get_kind(o):
    """Return the kind of an object"""
    return o.kind
    
    
def get_id(o):
    """Return the identifier for an object"""
    return o.id
    
    
def get_components(o):
    """Return list of all components in an object"""
    return o.components


def find_by_kind(o, wanted_kind):
    """Find all components of a desired kind inside this object"""
    return [c for c in get_components(o) 
                if obnam.cmp.get_kind(c) == wanted_kind]


def find_strings_by_kind(o, wanted_kind):
    """Find all components of a desired kind, return their string values"""
    return [obnam.cmp.get_string_value(c) 
                for c in find_by_kind(o, wanted_kind)]


def find_varints_by_kind(o, wanted_kind):
    """Find all components of a desired kind, return their varint values"""
    return [obnam.cmp.get_varint_value(c) 
                for c in find_by_kind(o, wanted_kind)]


def first_by_kind(o, wanted_kind):
    """Find first component of a desired kind"""
    for c in get_components(o):
        if obnam.cmp.get_kind(c) == wanted_kind:
            return c
    return None


def first_string_by_kind(o, wanted_kind):
    """Find string value of first component of a desired kind"""
    c = first_by_kind(o, wanted_kind)
    if c:
        return obnam.cmp.get_string_value(c)
    else:
        return None


def first_varint_by_kind(o, wanted_kind):
    """Find string value of first component of a desired kind"""
    c = first_by_kind(o, wanted_kind)
    if c:
        return obnam.cmp.get_varint_value(c)
    else:
        return None


def encode(o):
    """Encode an object as a string"""
    id = obnam.cmp.create(obnam.cmp.CMP_OBJID, o.id)
    kind = obnam.cmp.create(obnam.cmp.CMP_OBJKIND, 
                                     obnam.varint.encode(o.kind))
    list = [id, kind] + get_components(o)
    list = [obnam.cmp.encode(c) for c in list]
    return "".join(list)


def decode(encoded, pos):
    """Decode an object from a string"""
    list = []
    while pos < len(encoded):
        (c, pos) = obnam.cmp.decode(encoded, pos)
        list.append(c)
    o = create("", 0)
    for c in list:
        if c.kind == obnam.cmp.CMP_OBJID:
            o.id = obnam.cmp.get_string_value(c)
        elif c.kind == obnam.cmp.CMP_OBJKIND:
            o.kind = obnam.cmp.get_string_value(c)
            (o.kind, _) = obnam.varint.decode(o.kind, 0)
        else:
            add(o, c)
    return o


def queue_create():
    """Create an empty object queue"""
    return []


def queue_clear(oq):
    """Remove all objects from an object queue"""
    del oq[:]


def queue_add(oq, object_id, object):
    """Add an encoded object into an object queue"""
    oq.append((object_id, object))


def queue_is_empty(oq):
    """Is an object queue empty?"""
    return len(oq) == 0


def queue_combined_size(oq):
    """Return the combined size of all objects in an object queue"""
    return sum([len(x[1]) for x in oq])


def queue_ids(oq):
    """Return identifiers for all the objects in the object queue"""
    return [x[0] for x in oq]


def block_create_from_object_queue(blkid, oq):
    """Create a block from an object queue"""
    blkid = obnam.cmp.create(obnam.cmp.CMP_BLKID, blkid)
    objects = [obnam.cmp.create(obnam.cmp.CMP_OBJECT, x[1])
               for x in oq]
    return "".join([BLOCK_COOKIE] + 
                   [obnam.cmp.encode(c) for c in [blkid] + objects])


def block_decode(block):
    """Return list of decoded components in block, or None on error"""
    if block.startswith(BLOCK_COOKIE):
        return obnam.cmp.decode_all(block, len(BLOCK_COOKIE))
    else:
        return None


def signature_object_encode(objid, sigdata):
    c = obnam.cmp.create(obnam.cmp.CMP_SIGDATA, sigdata)
    o = create(objid, OBJ_SIG)
    add(o, c)
    return encode(o)


def normalize_stat_result(stat_result):
    """Create a new, normalized object from the return value of os.stat
    
    The normalized value has the st_xxx fields that the return value of
    os.stat has, but two normalized values may be safely compared for
    equality. 
    
    """
    
    fields = [x for x in dir(stat_result) if x.startswith("st_")]
    o = {}
    for x in fields:
        o[x] = int(stat_result.__getattribute__(x))
    return o


def inode_object_encode(objid, stat_result, sig_id, contents_id):
    """Create an inode object from the return value of os.stat"""
    o = create(objid, OBJ_INODE)

    st = stat_result

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
            c = obnam.cmp.create(kind, n)
            add(o, c)

    if sig_id:
        c = obnam.cmp.create(obnam.cmp.CMP_SIGREF, sig_id)
        add(o, c)
    if contents_id:
        c = obnam.cmp.create(obnam.cmp.CMP_CONTREF, contents_id)
        add(o, c)

    return encode(o)
    
    
class UnknownInodeField(ExceptionBase):

    def __init__(self, kind):
        self._msg = "Unknown field in inode object: %d" % kind


class NotAnInode(ExceptionBase):

    def __init__(self, okind):
        self._msg = "Object kind is not inode: %d" % okind


def inode_object_decode(inode):
    """Decode an inode object, return objid and what os.stat returns"""
    stat_results = {}
    list = obnam.cmp.decode_all(inode, 0)

    id = obnam.cmp.first_string_by_kind(list, obnam.cmp.CMP_OBJID)
    kind = obnam.cmp.first_varint_by_kind(list, obnam.cmp.CMP_OBJKIND)
    sigref = obnam.cmp.first_string_by_kind(list, obnam.cmp.CMP_SIGREF)
    contref = obnam.cmp.first_string_by_kind(list, 
                                                obnam.cmp.CMP_CONTREF)

    if kind != OBJ_INODE:
        raise NotAnInode(kind)
    o = create(id, kind)

    varint_items = {
        obnam.cmp.CMP_ST_MODE: "st_mode",
        obnam.cmp.CMP_ST_INO: "st_ino",
        obnam.cmp.CMP_ST_DEV: "st_dev",
        obnam.cmp.CMP_ST_NLINK: "st_nlink",
        obnam.cmp.CMP_ST_UID: "st_uid",
        obnam.cmp.CMP_ST_GID: "st_gid",
        obnam.cmp.CMP_ST_SIZE: "st_size",
        obnam.cmp.CMP_ST_ATIME: "st_atime",
        obnam.cmp.CMP_ST_MTIME: "st_mtime",
        obnam.cmp.CMP_ST_CTIME: "st_ctime",
        obnam.cmp.CMP_ST_BLOCKS: "st_blocks",
        obnam.cmp.CMP_ST_BLKSIZE: "st_blksize",
        obnam.cmp.CMP_ST_RDEV: "st_rdev",
    }
    for kind in varint_items:
        n = obnam.cmp.first_varint_by_kind(list, kind)
        if n is not None:
            stat_results[varint_items[kind]] = n

    return id, stat_results, sigref, contref


def generation_object_encode(objid, filelist_id):
    """Encode a generation object, from list of filename, inode_id pairs"""
    o = create(objid, OBJ_GEN)
    c = obnam.cmp.create(obnam.cmp.CMP_FILELISTREF, filelist_id)
    add(o, c)
    return encode(o)


def generation_object_decode(gen):
    """Decode a generation object into objid, file list ref"""

    o = decode(gen, 0)
    return o.id, first_string_by_kind(o, obnam.cmp.CMP_FILELISTREF)


def host_block_encode(host_id, gen_ids, map_block_ids, contmap_block_ids):
    """Encode a new block with a host object"""
    o = create(host_id, OBJ_HOST)
    
    c = obnam.cmp.create(obnam.cmp.CMP_FORMATVERSION, FORMAT_VERSION)
    add(o, c)

    for gen_id in gen_ids:
        c = obnam.cmp.create(obnam.cmp.CMP_GENREF, gen_id)
        add(o, c)
    
    for map_block_id in map_block_ids:
        c = obnam.cmp.create(obnam.cmp.CMP_MAPREF, map_block_id)
        add(o, c)
    
    for map_block_id in contmap_block_ids:
        c = obnam.cmp.create(obnam.cmp.CMP_CONTMAPREF, map_block_id)
        add(o, c)

    oq = queue_create()
    queue_add(oq, host_id, encode(o))
    block = block_create_from_object_queue(host_id, oq)
    return block


def host_block_decode(block):
    """Decode a host block"""
    
    list = block_decode(block)
    
    host_id = obnam.cmp.first_string_by_kind(list, obnam.cmp.CMP_BLKID)
    
    gen_ids = []
    map_ids = []
    contmap_ids = []

    objparts = obnam.cmp.find_by_kind(list, obnam.cmp.CMP_OBJECT)
    for objpart in objparts:
        subs = obnam.cmp.get_subcomponents(objpart)
        gen_ids += obnam.cmp.find_strings_by_kind(subs, 
                                                    obnam.cmp.CMP_GENREF)
        map_ids += obnam.cmp.find_strings_by_kind(subs, 
                                                    obnam.cmp.CMP_MAPREF)
        contmap_ids += obnam.cmp.find_strings_by_kind(subs, 
                                                obnam.cmp.CMP_CONTMAPREF)

    return host_id, gen_ids, map_ids, contmap_ids
