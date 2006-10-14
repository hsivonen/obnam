import uuid

from wibbrlib.exception import WibbrException
import wibbrlib.cmp
import wibbrlib.varint


# Constants of object types

_object_types = {}

def _define_type(code, name):
    assert code not in _object_types
    assert name not in _object_types.values()
    _object_types[code] = name
    return code

OBJ_FILEPART     = _define_type(1, "OBJ_FILEPART")
OBJ_INODE        = _define_type(2, "OBJ_INODE")
OBJ_GEN          = _define_type(3, "OBJ_GEN")
OBJ_SIG          = _define_type(4, "OBJ_SIG")
OBJ_HOST         = _define_type(5, "OBJ_HOST")
OBJ_FILECONTENTS = _define_type(6, "OBJ_FILECONTENTS")


def type_name(type):
    """Return a textual name for a numeric object type"""
    return _object_types.get(type, "OBJ_UNKNOWN")


def object_id_new():
    """Return a string that is a universally unique ID for an object"""
    return str(uuid.uuid4())


class Object:

    def __init__(self):
        self.id = None
        self.type = None
        self.components = []
        
        
def create(id, type):
    """Create a new backup object"""
    o = Object()
    o.id = id
    o.type = type
    return o


def add(o, c):
    """Add a component to an object"""
    o.components.append(c)


def get_type(o):
    """Return the type of an object"""
    return o.type
    
    
def get_id(o):
    """Return the identifier for an object"""
    return o.id
    
    
def get_components(o):
    """Return list of all components in an object"""
    return o.components


def find_by_type(o, wanted_type):
    """Find all components of a desired type inside this object"""
    return [c for c in get_components(o) 
                if wibbrlib.cmp.get_type(c) == wanted_type]


def find_strings_by_type(o, wanted_type):
    """Find all components of a desired type, return their string values"""
    return [wibbrlib.cmp.get_string_value(c) 
                for c in find_by_type(o, wanted_type)]


def find_varints_by_type(o, wanted_type):
    """Find all components of a desired type, return their varint values"""
    return [wibbrlib.cmp.get_varint_value(c) 
                for c in find_by_type(o, wanted_type)]


def first_by_type(o, wanted_type):
    """Find first component of a desired type"""
    for c in get_components(o):
        if wibbrlib.cmp.get_type(c) == wanted_type:
            return c
    return None


def first_string_by_type(o, wanted_type):
    """Find string value of first component of a desired type"""
    c = first_by_type(o, wanted_type)
    if c:
        return wibbrlib.cmp.get_string_value(c)
    else:
        return None


def first_varint_by_type(o, wanted_type):
    """Find string value of first component of a desired type"""
    c = first_by_type(o, wanted_type)
    if c:
        return wibbrlib.cmp.get_varint_value(c)
    else:
        return None


def encode(o):
    """Encode an object as a string"""
    id = wibbrlib.cmp.create(wibbrlib.cmp.CMP_OBJID, o.id)
    type = wibbrlib.cmp.create(wibbrlib.cmp.CMP_OBJTYPE, 
                                     wibbrlib.varint.encode(o.type))
    list = [id, type] + get_components(o)
    list = [wibbrlib.cmp.encode(c) for c in list]
    return "".join(list)


def decode(encoded, pos):
    """Decode an object from a string"""
    list = []
    while pos < len(encoded):
        (c, pos) = wibbrlib.cmp.decode(encoded, pos)
        list.append(c)
    o = create("", 0)
    for c in list:
        if c.type == wibbrlib.cmp.CMP_OBJID:
            o.id = wibbrlib.cmp.get_string_value(c)
        elif c.type == wibbrlib.cmp.CMP_OBJTYPE:
            o.type = wibbrlib.cmp.get_string_value(c)
            (o.type, _) = wibbrlib.varint.decode(o.type, 0)
        else:
            add(o, c)
    return o


def object_queue_create():
    """Create an empty object queue"""
    return []


def object_queue_clear(oq):
    """Remove all objects from an object queue"""
    del oq[:]


def object_queue_add(oq, object_id, object):
    """Add an encoded object into an object queue"""
    oq.append((object_id, object))


def object_queue_combined_size(oq):
    """Return the combined size of all objects in an object queue"""
    return sum([len(x[1]) for x in oq])


def object_queue_ids(oq):
    """Return identifiers for all the objects in the object queue"""
    return [x[0] for x in oq]


def block_create_from_object_queue(blkid, oq):
    """Create a block from an object queue"""
    blkid = wibbrlib.cmp.create(wibbrlib.cmp.CMP_BLKID, blkid)
    objects = [wibbrlib.cmp.create(wibbrlib.cmp.CMP_OBJPART, x[1])
                for x in oq]
    return "".join([wibbrlib.cmp.encode(c) for c in [blkid] + objects])


def signature_object_encode(objid, sigdata):
    c = wibbrlib.cmp.create(wibbrlib.cmp.CMP_SIGDATA, sigdata)
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
        o[x] = stat_result.__getattribute__(x)
    return o


def inode_object_encode(objid, stat_result, sig_id, contents_id):
    """Create an inode object from the return value of os.stat"""
    o = create(objid, OBJ_INODE)

    st = stat_result

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
    for type, key in items:
        if key in st:
            n = wibbrlib.varint.encode(st[key])
            c = wibbrlib.cmp.create(type, n)
            add(o, c)

    if sig_id:
        c = wibbrlib.cmp.create(wibbrlib.cmp.CMP_SIGREF, sig_id)
        add(o, c)
    if contents_id:
        c = wibbrlib.cmp.create(wibbrlib.cmp.CMP_CONTREF, contents_id)
        add(o, c)

    return encode(o)
    
    
class UnknownInodeField(WibbrException):

    def __init__(self, type):
        self._msg = "Unknown field in inode object: %d" % type


class NotAnInode(WibbrException):

    def __init__(self, otype):
        self._msg = "Object type is not inode: %d" % otype


def inode_object_decode(inode):
    """Decode an inode object, return objid and what os.stat returns"""
    stat_results = {}
    list = wibbrlib.cmp.decode_all(inode, 0)

    id = wibbrlib.cmp.first_string_by_type(list, wibbrlib.cmp.CMP_OBJID)
    type = wibbrlib.cmp.first_varint_by_type(list, wibbrlib.cmp.CMP_OBJTYPE)
    sigref = wibbrlib.cmp.first_string_by_type(list, wibbrlib.cmp.CMP_SIGREF)
    contref = wibbrlib.cmp.first_string_by_type(list, 
                                                wibbrlib.cmp.CMP_CONTREF)

    if type != OBJ_INODE:
        raise NotAnInode(type)
    o = create(id, type)

    varint_items = {
        wibbrlib.cmp.CMP_ST_MODE: "st_mode",
        wibbrlib.cmp.CMP_ST_INO: "st_ino",
        wibbrlib.cmp.CMP_ST_DEV: "st_dev",
        wibbrlib.cmp.CMP_ST_NLINK: "st_nlink",
        wibbrlib.cmp.CMP_ST_UID: "st_uid",
        wibbrlib.cmp.CMP_ST_GID: "st_gid",
        wibbrlib.cmp.CMP_ST_SIZE: "st_size",
        wibbrlib.cmp.CMP_ST_ATIME: "st_atime",
        wibbrlib.cmp.CMP_ST_MTIME: "st_mtime",
        wibbrlib.cmp.CMP_ST_CTIME: "st_ctime",
        wibbrlib.cmp.CMP_ST_BLOCKS: "st_blocks",
        wibbrlib.cmp.CMP_ST_BLKSIZE: "st_blksize",
        wibbrlib.cmp.CMP_ST_RDEV: "st_rdev",
    }
    for type in varint_items:
        n = wibbrlib.cmp.first_varint_by_type(list, type)
        if n is not None:
            stat_results[varint_items[type]] = n

    return id, stat_results, sigref, contref


def generation_object_encode(objid, pairs):
    """Encode a generation object, from list of filename, inode_id pairs"""
    o = create(objid, OBJ_GEN)
    for filename, inode_id in pairs:
        cf = wibbrlib.cmp.create(wibbrlib.cmp.CMP_FILENAME, filename)
        ci = wibbrlib.cmp.create(wibbrlib.cmp.CMP_INODEREF, inode_id)
        c = wibbrlib.cmp.create(wibbrlib.cmp.CMP_NAMEIPAIR, [cf, ci])
        add(o, c)
    return encode(o)


def generation_object_decode(gen):
    """Decode a generation object into objid, list of name, inode_id pairs"""

    o = decode(gen, 0)
    list = find_by_type(o, wibbrlib.cmp.CMP_NAMEIPAIR)
    makepair = lambda subs: \
        (wibbrlib.cmp.first_string_by_type(subs, wibbrlib.cmp.CMP_FILENAME),
         wibbrlib.cmp.first_string_by_type(subs, wibbrlib.cmp.CMP_INODEREF))
    list = [makepair(wibbrlib.cmp.get_subcomponents(c)) for c in list]
    return o.id, list


def host_block_encode(host_id, gen_ids, map_block_ids):
    """Encode a new block with a host object"""
    o = create(host_id, OBJ_HOST)

    gen_ids = [wibbrlib.cmp.create(wibbrlib.cmp.CMP_GENREF, x) 
               for x in gen_ids]
    c = wibbrlib.cmp.create(wibbrlib.cmp.CMP_GENLIST, gen_ids)
    add(o, c)
    
    for map_block_id in map_block_ids:
        c = wibbrlib.cmp.create(wibbrlib.cmp.CMP_MAPREF, map_block_id)
        add(o, c)

    oq = object_queue_create()
    object_queue_add(oq, host_id, encode(o))
    block = block_create_from_object_queue(host_id, oq)
    return block


def host_block_decode(block):
    """Decode a host block"""
    
    list = wibbrlib.cmp.decode_all(block, 0)
    
    host_id = wibbrlib.cmp.first_string_by_type(list, wibbrlib.cmp.CMP_BLKID)
    
    map_ids = []
    gen_ids = []

    objparts = wibbrlib.cmp.find_by_type(list, wibbrlib.cmp.CMP_OBJPART)
    for objpart in objparts:
        subs = wibbrlib.cmp.get_subcomponents(objpart)
        map_ids += wibbrlib.cmp.find_strings_by_type(subs, 
                                                    wibbrlib.cmp.CMP_MAPREF)

        genlists = wibbrlib.cmp.find_by_type(subs, wibbrlib.cmp.CMP_GENLIST)
        for genlist in genlists:
            subs2 = wibbrlib.cmp.get_subcomponents(genlist)
            gen_ids += wibbrlib.cmp.find_strings_by_type(subs2,
                                                    wibbrlib.cmp.CMP_GENREF)

    return host_id, gen_ids, map_ids
