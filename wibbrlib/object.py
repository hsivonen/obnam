import uuid

from wibbrlib.exception import WibbrException
import wibbrlib.component


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


def object_type_name(type):
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


def object_encode(objid, objtype, encoded_components):
    """Encode an object, given id, type, and list of encoded components"""
    objid = wibbrlib.component.create(wibbrlib.component.CMP_OBJID, objid)
    objid = wibbrlib.component.encode(objid)
    objtype = wibbrlib.component.create(wibbrlib.component.CMP_OBJTYPE, wibbrlib.varint.varint_encode(objtype))
    objtype = wibbrlib.component.encode(objtype)
    return objid + objtype + "".join(encoded_components)


def object_decode(str, pos):
    """Decode an object, return components as list of (type, data)"""
    pairs = []
    for type, data in wibbrlib.component.component_decode_all(str, pos):
        if type == wibbrlib.component.CMP_OBJTYPE:
            (data, _) = wibbrlib.varint.varint_decode(data, 0)
        pairs.append((type, data))
    return pairs


def object_queue_create():
    """Create an empty object queue"""
    return []


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
    blkid = wibbrlib.component.component_encode(wibbrlib.component.CMP_BLKID, blkid)
    objects = [wibbrlib.component.component_encode(wibbrlib.component.CMP_OBJPART, x[1]) for x in oq]
    return blkid + "".join(objects)


def signature_object_encode(objid, sigdata):
    sigdata_component = wibbrlib.component.component_encode(wibbrlib.component.CMP_SIGDATA, sigdata)
    object = object_encode(objid, OBJ_SIG, [sigdata_component])
    return object


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
    fields = []
    st = stat_result
    fields.append(wibbrlib.component.component_encode(wibbrlib.component.CMP_ST_MODE, wibbrlib.varint.varint_encode(st["st_mode"])))
    fields.append(wibbrlib.component.component_encode(wibbrlib.component.CMP_ST_INO, wibbrlib.varint.varint_encode(st["st_ino"])))
    fields.append(wibbrlib.component.component_encode(wibbrlib.component.CMP_ST_DEV, wibbrlib.varint.varint_encode(st["st_dev"])))
    fields.append(wibbrlib.component.component_encode(wibbrlib.component.CMP_ST_NLINK, wibbrlib.varint.varint_encode(st["st_nlink"])))
    fields.append(wibbrlib.component.component_encode(wibbrlib.component.CMP_ST_UID, wibbrlib.varint.varint_encode(st["st_uid"])))
    fields.append(wibbrlib.component.component_encode(wibbrlib.component.CMP_ST_GID, wibbrlib.varint.varint_encode(st["st_gid"])))
    fields.append(wibbrlib.component.component_encode(wibbrlib.component.CMP_ST_SIZE, wibbrlib.varint.varint_encode(st["st_size"])))
    fields.append(wibbrlib.component.component_encode(wibbrlib.component.CMP_ST_ATIME, wibbrlib.varint.varint_encode(st["st_atime"])))
    fields.append(wibbrlib.component.component_encode(wibbrlib.component.CMP_ST_MTIME, wibbrlib.varint.varint_encode(st["st_mtime"])))
    fields.append(wibbrlib.component.component_encode(wibbrlib.component.CMP_ST_CTIME, wibbrlib.varint.varint_encode(st["st_ctime"])))
    if "st_blocks" in st:
        fields.append(wibbrlib.component.component_encode(wibbrlib.component.CMP_ST_BLOCKS, 
                                       wibbrlib.varint.varint_encode(st["st_blocks"])))
    if "st_blksize" in st:
        fields.append(wibbrlib.component.component_encode(wibbrlib.component.CMP_ST_BLKSIZE, 
                                       wibbrlib.varint.varint_encode(st["st_blksize"])))
    if "st_rdev" in st:
        fields.append(wibbrlib.component.component_encode(wibbrlib.component.CMP_ST_RDEV, 
                                       wibbrlib.varint.varint_encode(st["st_rdev"])))
    if sig_id:
        fields.append(wibbrlib.component.component_encode(wibbrlib.component.CMP_SIGREF, sig_id))
    if contents_id:
        fields.append(wibbrlib.component.component_encode(wibbrlib.component.CMP_CONTREF, contents_id))
    return object_encode(objid, OBJ_INODE, fields)
    
    
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
    for type, data in wibbrlib.component.component_decode_all(inode, 0):
        if type == wibbrlib.component.CMP_OBJID:
            objid = data
        elif type == wibbrlib.component.CMP_OBJTYPE:
            (otype, _) = wibbrlib.varint.varint_decode(data, 0)
            if otype != OBJ_INODE:
                raise NotAnInode(otype)
        elif type == wibbrlib.component.CMP_ST_MODE:
            stat_results["st_mode"] = wibbrlib.varint.varint_decode(data, 0)[0]
        elif type == wibbrlib.component.CMP_ST_INO:
            stat_results["st_ino"] = wibbrlib.varint.varint_decode(data, 0)[0]
        elif type == wibbrlib.component.CMP_ST_DEV:
            stat_results["st_dev"] = wibbrlib.varint.varint_decode(data, 0)[0]
        elif type == wibbrlib.component.CMP_ST_NLINK:
            stat_results["st_nlink"] = wibbrlib.varint.varint_decode(data, 0)[0]
        elif type == wibbrlib.component.CMP_ST_UID:
            stat_results["st_uid"] = wibbrlib.varint.varint_decode(data, 0)[0]
        elif type == wibbrlib.component.CMP_ST_GID:
            stat_results["st_gid"] = wibbrlib.varint.varint_decode(data, 0)[0]
        elif type == wibbrlib.component.CMP_ST_SIZE:
            stat_results["st_size"] = wibbrlib.varint.varint_decode(data, 0)[0]
        elif type == wibbrlib.component.CMP_ST_ATIME:
            stat_results["st_atime"] = wibbrlib.varint.varint_decode(data, 0)[0]
        elif type == wibbrlib.component.CMP_ST_MTIME:
            stat_results["st_mtime"] = wibbrlib.varint.varint_decode(data, 0)[0]
        elif type == wibbrlib.component.CMP_ST_CTIME:
            stat_results["st_ctime"] = wibbrlib.varint.varint_decode(data, 0)[0]
        elif type == wibbrlib.component.CMP_ST_BLOCKS:
            stat_results["st_blocks"] = wibbrlib.varint.varint_decode(data, 0)[0]
        elif type == wibbrlib.component.CMP_ST_BLKSIZE:
            stat_results["st_blksize"] = wibbrlib.varint.varint_decode(data, 0)[0]
        elif type == wibbrlib.component.CMP_ST_RDEV:
            stat_results["st_rdev"] = wibbrlib.varint.varint_decode(data, 0)[0]
        elif type == wibbrlib.component.CMP_SIGREF:
            sigref = data
        elif type == wibbrlib.component.CMP_CONTREF:
            contref = data
        else:
            raise UnknownInodeField(type)
    return objid, stat_results, sigref, contref


def generation_object_encode(objid, pairs):
    """Encode a generation object, from list of filename, inode_id pairs"""
    components = []
    for filename, inode_id in pairs:
        cf = wibbrlib.component.component_encode(wibbrlib.component.CMP_FILENAME, filename)
        ci = wibbrlib.component.component_encode(wibbrlib.component.CMP_INODEREF, inode_id)
        c = wibbrlib.component.component_encode(wibbrlib.component.CMP_NAMEIPAIR, cf + ci)
        components.append(c)
    return object_encode(objid, OBJ_GEN, components)


class UnknownGenerationComponent(WibbrException):

    def __init__(self, type):
        self._msg = "Unknown component in generation: %s (%d)" % \
            (wibbrlib.component.component_type_name(type), type)


class NameInodePairHasTooManyComponents(WibbrException):

    def __init__(self):
        self._msg = "Name/inode pair has too many components"


class InvalidNameInodePair(WibbrException):

    def __init__(self):
        self._msg = "Name/inode pair does not consist of name and inode"


class WrongObjectType(WibbrException):

    def __init__(self, actual, wanted):
        self._msg = "Object is of type %s (%d), wanted %s (%d)" % \
            (object_type_name(actual), actual, 
             object_type_name(wanted), wanted)


def generation_object_decode(gen):
    """Decode a generation object into objid, list of name, inode_id pairs"""
    objid = None
    pairs = []
    for type, data in wibbrlib.component.component_decode_all(gen, 0):
        if type == wibbrlib.component.CMP_OBJID:
            objid = data
        elif type == wibbrlib.component.CMP_OBJTYPE:
            (objtype, _) = wibbrlib.varint.varint_decode(data, 0)
            if objtype != OBJ_GEN:
                raise WrongObjectType(objtype, OBJ_GEN)
        elif type == wibbrlib.component.CMP_NAMEIPAIR:
            components = wibbrlib.component.component_decode_all(data, 0)
            if len(components) != 2:
                raise NameInodePairHasTooManyComponents()
            (nitype1, nidata1) = components[0]
            (nitype2, nidata2) = components[1]
            if nitype1 == wibbrlib.component.CMP_INODEREF and nitype2 == wibbrlib.component.CMP_FILENAME:
                inode_id = nidata1
                filename = nidata2
            elif nitype2 == wibbrlib.component.CMP_INODEREF and nitype1 == wibbrlib.component.CMP_FILENAME:
                inode_id = nidata2
                filename = nidata1
            else:
                raise InvalidNameInodePair()
            pairs.append((filename, inode_id))
        else:
            raise UnknownGenerationComponent(type)
            
    return objid, pairs


def host_block_encode(host_id, gen_ids, map_block_ids):
    """Encode a new block with a host object"""
    list = []

    gen_ids = [wibbrlib.component.component_encode(wibbrlib.component.CMP_GENREF, x) for x in gen_ids]    
    list.append(wibbrlib.component.component_encode(wibbrlib.component.CMP_GENLIST, "".join(gen_ids)))
    
    for map_block_id in map_block_ids:
        list.append(wibbrlib.component.component_encode(wibbrlib.component.CMP_MAPREF, map_block_id))

    object = object_encode(host_id, OBJ_HOST, list)
    oq = object_queue_create()
    object_queue_add(oq, host_id, object)
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
            (object_type_name(objtype), objtype)


class UnknownHostObjectComponentType(WibbrException):

    def __init__(self, type):
        self._msg = \
            "Host object contains component of unexpected type %s (%d)" % \
                (wibbrlib.component.component_type_name(type), type)


class UnknownHostBlockComponentType(WibbrException):

    def __init__(self, type):
        self._msg = \
            "Host block contains component of unexpected type %s (%d)" % \
                (wibbrlib.component.component_type_name(type), type)


class UnknownGenlistComponentType(WibbrException):

    def __init__(self, type):
        self._msg = \
            "Host block's generation list contains component of " + \
            "unexpectedtype %s (%d)" % \
                (wibbrlib.component.component_type_name(type), type)


def genlist_decode(genlist):
    gen_ids = []
    for type, data in wibbrlib.component.component_decode_all(genlist, 0):
        if type == wibbrlib.component.CMP_GENREF:
            gen_ids.append(data)
        else:
            raise UnknownGenlistComponentType(type)
    return gen_ids


def host_block_decode(block):
    """Decode a host block"""
    
    host_id = None
    gen_ids = []
    map_ids = []
    
    for type, data in wibbrlib.component.component_decode_all(block, 0):
        if type == wibbrlib.component.CMP_BLKID:
            if host_id is None:
                host_id = data
            elif host_id != data:
                raise ConfusedHostId(host_id, data)
        elif type == wibbrlib.component.CMP_OBJPART:
            for type2, data2 in wibbrlib.component.component_decode_all(data, 0):
                if type2 == wibbrlib.component.CMP_OBJID:
                    if host_id is None:
                        host_id = data2
                    elif host_id != data2:
                        raise ConfusedHostId(host_id, data2)
                elif type2 == wibbrlib.component.CMP_OBJTYPE:
                    (objtype, _) = wibbrlib.varint.varint_decode(data2, 0)
                    if objtype != OBJ_HOST:
                        raise HostBlockHasWrongObjectType(objtype)
                elif type2 == wibbrlib.component.CMP_GENLIST:
                    gen_ids = genlist_decode(data2)
                elif type2 == wibbrlib.component.CMP_MAPREF:
                    map_ids.append(data2)
                else:
                    raise UnknownHostObjectComponentType(type2)
        else:
            raise UnknownHostBlockComponentType(type)

    return host_id, gen_ids, map_ids
