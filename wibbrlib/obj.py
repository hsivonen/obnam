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
    objid = None
    stat_results = {}
    sigref = None
    contref = None
    for c in wibbrlib.cmp.decode_all(inode, 0):
        type = wibbrlib.cmp.get_type(c)
        if wibbrlib.cmp.is_composite(c):
            data = None
        else:
            data = wibbrlib.cmp.get_string_value(c)
        if type == wibbrlib.cmp.CMP_OBJID:
            objid = data
        elif type == wibbrlib.cmp.CMP_OBJTYPE:
            (otype, _) = wibbrlib.varint.decode(data, 0)
            if otype != OBJ_INODE:
                raise NotAnInode(otype)
        elif type == wibbrlib.cmp.CMP_ST_MODE:
            stat_results["st_mode"] = wibbrlib.varint.decode(data, 0)[0]
        elif type == wibbrlib.cmp.CMP_ST_INO:
            stat_results["st_ino"] = wibbrlib.varint.decode(data, 0)[0]
        elif type == wibbrlib.cmp.CMP_ST_DEV:
            stat_results["st_dev"] = wibbrlib.varint.decode(data, 0)[0]
        elif type == wibbrlib.cmp.CMP_ST_NLINK:
            stat_results["st_nlink"] = wibbrlib.varint.decode(data, 0)[0]
        elif type == wibbrlib.cmp.CMP_ST_UID:
            stat_results["st_uid"] = wibbrlib.varint.decode(data, 0)[0]
        elif type == wibbrlib.cmp.CMP_ST_GID:
            stat_results["st_gid"] = wibbrlib.varint.decode(data, 0)[0]
        elif type == wibbrlib.cmp.CMP_ST_SIZE:
            stat_results["st_size"] = wibbrlib.varint.decode(data, 0)[0]
        elif type == wibbrlib.cmp.CMP_ST_ATIME:
            stat_results["st_atime"] = wibbrlib.varint.decode(data, 0)[0]
        elif type == wibbrlib.cmp.CMP_ST_MTIME:
            stat_results["st_mtime"] = wibbrlib.varint.decode(data, 0)[0]
        elif type == wibbrlib.cmp.CMP_ST_CTIME:
            stat_results["st_ctime"] = wibbrlib.varint.decode(data, 0)[0]
        elif type == wibbrlib.cmp.CMP_ST_BLOCKS:
            stat_results["st_blocks"] = wibbrlib.varint.decode(data, 0)[0]
        elif type == wibbrlib.cmp.CMP_ST_BLKSIZE:
            stat_results["st_blksize"] = wibbrlib.varint.decode(data, 0)[0]
        elif type == wibbrlib.cmp.CMP_ST_RDEV:
            stat_results["st_rdev"] = wibbrlib.varint.decode(data, 0)[0]
        elif type == wibbrlib.cmp.CMP_SIGREF:
            sigref = data
        elif type == wibbrlib.cmp.CMP_CONTREF:
            contref = data
        else:
            raise UnknownInodeField(type)
    return objid, stat_results, sigref, contref


def generation_object_encode(objid, pairs):
    """Encode a generation object, from list of filename, inode_id pairs"""
    o = create(objid, OBJ_GEN)
    for filename, inode_id in pairs:
        cf = wibbrlib.cmp.create(wibbrlib.cmp.CMP_FILENAME, 
                                       filename)
        ci = wibbrlib.cmp.create(wibbrlib.cmp.CMP_INODEREF, 
                                       inode_id)
        c = wibbrlib.cmp.create(wibbrlib.cmp.CMP_NAMEIPAIR, 
                                      [cf, ci])
        add(o, c)
    return encode(o)


class UnknownGenerationComponent(WibbrException):

    def __init__(self, type):
        self._msg = "Unknown component in generation: %s (%d)" % \
            (wibbrlib.cmp.type_name(type), type)


class NameInodePairHasTooManyComponents(WibbrException):

    def __init__(self):
        self._msg = "Name/inode pair has too many components"


class InvalidNameInodePair(WibbrException):

    def __init__(self):
        self._msg = "Name/inode pair does not consist of name and inode"


class WrongObjectType(WibbrException):

    def __init__(self, actual, wanted):
        self._msg = "Object is of type %s (%d), wanted %s (%d)" % \
            (type_name(actual), actual, 
             type_name(wanted), wanted)


def generation_object_decode(gen):
    """Decode a generation object into objid, list of name, inode_id pairs"""
    objid = None
    pairs = []
    for c in wibbrlib.cmp.decode_all(gen, 0):
        type = wibbrlib.cmp.get_type(c)
        if wibbrlib.cmp.is_composite(c):
            data = None
        else:
            data = wibbrlib.cmp.get_string_value(c)
        if type == wibbrlib.cmp.CMP_OBJID:
            objid = data
        elif type == wibbrlib.cmp.CMP_OBJTYPE:
            (objtype, _) = wibbrlib.varint.decode(data, 0)
            if objtype != OBJ_GEN:
                raise WrongObjectType(objtype, OBJ_GEN)
        elif type == wibbrlib.cmp.CMP_NAMEIPAIR:
            components = wibbrlib.cmp.get_subcomponents(c)
            if len(components) != 2:
                raise NameInodePairHasTooManyComponents()
            t1 = wibbrlib.cmp.get_type(components[0])
            t2 = wibbrlib.cmp.get_type(components[1])
            if t1 == wibbrlib.cmp.CMP_INODEREF and t2 == wibbrlib.cmp.CMP_FILENAME:
                inode_id = wibbrlib.cmp.get_string_value(components[0])
                filename = wibbrlib.cmp.get_string_value(components[1])
            elif t2 == wibbrlib.cmp.CMP_INODEREF and t1 == wibbrlib.cmp.CMP_FILENAME:
                inode_id = wibbrlib.cmp.get_string_value(components[1])
                filename = wibbrlib.cmp.get_string_value(components[0])
            else:
                raise InvalidNameInodePair()
            pairs.append((filename, inode_id))
        else:
            raise UnknownGenerationComponent(type)
            
    return objid, pairs


def host_block_encode(host_id, gen_ids, map_block_ids):
    """Encode a new block with a host object"""
    o = create(host_id, OBJ_HOST)

    gen_ids = [wibbrlib.cmp.create(wibbrlib.cmp.CMP_GENREF, x) 
               for x in gen_ids]
    c = wibbrlib.cmp.create(wibbrlib.cmp.CMP_GENLIST, gen_ids)
    add(o, c)
    
    for map_block_id in map_block_ids:
        c = wibbrlib.cmp.create(wibbrlib.cmp.CMP_MAPREF, 
                                      map_block_id)
        add(o, c)

    oq = object_queue_create()
    object_queue_add(oq, host_id, encode(o))
    block = block_create_from_object_queue(host_id, oq)
    return block


class ConfusedHostId(WibbrException):

    def __init__(self, id1, id2):
        self._msg = \
            "Host block contains contradictory host IDs: '%s' and '%s'" \
            % (id1, id2)


class HostBlockHasWrongObjectType(WibbrException):

    def __init__(self, objtype):
        self._msg = "Host block contains object of type %s (%d)" % \
            (type_name(objtype), objtype)


class UnknownHostObjectComponentType(WibbrException):

    def __init__(self, type):
        self._msg = \
            "Host object contains component of unexpected type %s (%d)" % \
                (wibbrlib.cmp.type_name(type), type)


class UnknownHostBlockComponentType(WibbrException):

    def __init__(self, type):
        self._msg = \
            "Host block contains component of unexpected type %s (%d)" % \
                (wibbrlib.cmp.type_name(type), type)


class UnknownGenlistComponentType(WibbrException):

    def __init__(self, type):
        self._msg = \
            "Host block's generation list contains component of " + \
            "unexpectedtype %s (%d)" % \
                (wibbrlib.cmp.type_name(type), type)


def genlist_decode(genlist):
    gen_ids = []
    for c in wibbrlib.cmp.decode_all(genlist, 0):
        type = wibbrlib.cmp.get_type(c)
        if type == wibbrlib.cmp.CMP_GENREF:
            gen_ids.append(wibbrlib.cmp.get_string_value(c))
        else:
            raise UnknownGenlistComponentType(type)
    return gen_ids


def host_block_decode(block):
    """Decode a host block"""
    
    host_id = None
    gen_ids = []
    map_ids = []
    
    for c in wibbrlib.cmp.decode_all(block, 0):
        type = wibbrlib.cmp.get_type(c)
        if wibbrlib.cmp.is_composite(c):
            data = None
        else:
            data = wibbrlib.cmp.get_string_value(c)
        if type == wibbrlib.cmp.CMP_BLKID:
            if host_id is None:
                host_id = data
            elif host_id != data:
                raise ConfusedHostId(host_id, data)
        elif type == wibbrlib.cmp.CMP_OBJPART:
            for c2 in wibbrlib.cmp.get_subcomponents(c):
                type2 = wibbrlib.cmp.get_type(c2)
                if wibbrlib.cmp.is_composite(c2):
                    data2 = None
                else:
                    data2 = wibbrlib.cmp.get_string_value(c2)
                if type2 == wibbrlib.cmp.CMP_OBJID:
                    if host_id is None:
                        host_id = data2
                    elif host_id != data2:
                        raise ConfusedHostId(host_id, data2)
                elif type2 == wibbrlib.cmp.CMP_OBJTYPE:
                    (objtype, _) = wibbrlib.varint.decode(data2, 0)
                    if objtype != OBJ_HOST:
                        raise HostBlockHasWrongObjectType(objtype)
                elif type2 == wibbrlib.cmp.CMP_GENLIST:
                    gen_ids = genlist_decode(data2)
                elif type2 == wibbrlib.cmp.CMP_MAPREF:
                    map_ids.append(data2)
                else:
                    raise UnknownHostObjectComponentType(type2)
        else:
            raise UnknownHostBlockComponentType(type)

    return host_id, gen_ids, map_ids
