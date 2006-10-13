"""Format data for presentation"""


import stat


def permissions(mode):
    """Return a string like "ls -l" to indicate the permissions"""

    ru = wu = xu = rg = wg = xg = ro = wo = xo = "-"

    if mode & stat.S_IRUSR:
        ru = "r"
    if mode & stat.S_IWUSR:
        wu = "w"
    if mode & stat.S_IXUSR:
        xu = "x"
    if mode & stat.S_ISUID:
        xu = "s"

    if mode & stat.S_IRGRP:
        rg = "r"
    if mode & stat.S_IWGRP:
        wg = "w"
    if mode & stat.S_IXGRP:
        xg = "x"
    if mode & stat.S_ISGID:
        xg = "s"

    if mode & stat.S_IROTH:
        ro = "r"
    if mode & stat.S_IWOTH:
        wo = "w"
    if mode & stat.S_IXOTH:
        xo = "x"
    if mode & stat.S_ISVTX:
        xo = "t"
    
    return ru + wu + xu + rg + wg + xg + ro + wo + xo
