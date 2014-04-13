/*
 * _obnammodule.c -- Python extensions for Obna
 *
 * Copyright (C) 2008-2014  Lars Wirzenius <liw@liw.fi>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
 */


/*
 * This is a Python extension module written for Obnam, the backup
 * software.
 *
 * This module provides a way to call the posix_fadvise function from
 * Python. Obnam uses this to use set the POSIX_FADV_SEQUENTIAL and
 * POSIX_FADV_DONTNEED flags, to make sure the kernel knows that it will
 * read files sequentially and that the data does not need to be cached.
 * This makes Obnam not trash the disk buffer cache, which is nice.
 */


#define _FILE_OFFSET_BITS 64

#include <Python.h>


#ifndef _XOPEN_SOURCE
#define _XOPEN_SOURCE 600
#endif
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include <stdlib.h>

#ifdef __FreeBSD__
    #include <sys/extattr.h>
    #define NO_NANOSECONDS 1
#else
    #include <sys/xattr.h>
    #define NO_NANOSECONDS 0
#endif


static PyObject *
fadvise_dontneed(PyObject *self, PyObject *args)
{
#if POSIX_FADV_DONTNEED
    int fd;
    /* Can't use off_t for offset and len, since PyArg_ParseTuple
       doesn't know it. */
    unsigned long long offset;
    unsigned long long len;
    int ret;

    if (!PyArg_ParseTuple(args, "iLL", &fd, &offset, &len))
        return NULL;
    ret = posix_fadvise(fd, offset, len, POSIX_FADV_DONTNEED);
    return Py_BuildValue("i", ret);
#else
    return Py_BuildValue("i", 0);
#endif
}


static PyObject *
utimensat_wrapper(PyObject *self, PyObject *args)
{
    int ret;
    const char *filename;
    long atime_sec, atime_nsec;
    long mtime_sec, mtime_nsec;
#if NO_NANOSECONDS
    struct timeval tv[2];
#else
    struct timespec tv[2];
#endif
    if (!PyArg_ParseTuple(args, "sllll",
                          &filename,
                          &atime_sec,
                          &atime_nsec,
                          &mtime_sec,
                          &mtime_nsec))
        return NULL;

#if NO_NANOSECONDS
    tv[0].tv_sec = atime_sec;
    tv[0].tv_usec = atime_nsec / 1000;
    tv[1].tv_sec = mtime_sec;
    tv[1].tv_usec = mtime_nsec / 1000;
    ret = lutimes(filename, tv);
#else
    tv[0].tv_sec = atime_sec;
    tv[0].tv_nsec = atime_nsec;
    tv[1].tv_sec = mtime_sec;
    tv[1].tv_nsec = mtime_nsec;
    ret = utimensat(AT_FDCWD, filename, tv, AT_SYMLINK_NOFOLLOW);
#endif
    if (ret == -1)
        ret = errno;
    return Py_BuildValue("i", ret);
}


/*
 * Since we can't set nanosecond mtime and atimes on some platforms, also
 * don't retrieve that level of precision from lstat(), so comparisons
 * work.
 */
static unsigned long long
remove_precision(unsigned long long nanoseconds)
{
#if NO_NANOSECONDS
    return nanoseconds - (nanoseconds % 1000);
#else
    return nanoseconds;
#endif
}


static PyObject *
lstat_wrapper(PyObject *self, PyObject *args)
{
    int ret;
    const char *filename;
    struct stat st = {0};

    if (!PyArg_ParseTuple(args, "s", &filename))
        return NULL;

    ret = lstat(filename, &st);
    if (ret == -1)
        ret = errno;

    return Py_BuildValue("iKKKKKKKLLLLKLKLK",
                         ret,
                         (unsigned long long) st.st_dev,
                         (unsigned long long) st.st_ino,
                         (unsigned long long) st.st_mode,
                         (unsigned long long) st.st_nlink,
                         (unsigned long long) st.st_uid,
                         (unsigned long long) st.st_gid,
                         (unsigned long long) st.st_rdev,
                         (long long) st.st_size,
                         (long long) st.st_blksize,
                         (long long) st.st_blocks,
                         (long long) st.st_atim.tv_sec,
                         remove_precision(st.st_atim.tv_nsec),
                         (long long) st.st_mtim.tv_sec,
                         remove_precision(st.st_mtim.tv_nsec),
                         (long long) st.st_ctim.tv_sec,
                         remove_precision(st.st_ctim.tv_nsec));
}


static PyObject *
llistxattr_wrapper(PyObject *self, PyObject *args)
{
    const char *filename;
    size_t bufsize;
    PyObject *o;
    char* buf;
    ssize_t n;

    if (!PyArg_ParseTuple(args, "s", &filename))
        return NULL;

#ifdef __FreeBSD__
    bufsize = extattr_list_link(filename, EXTATTR_NAMESPACE_USER, NULL, 0);
    buf = malloc(bufsize);
    if (buf == NULL) {
        Py_INCREF(Py_None);
        return Py_None;
    }
    n = extattr_list_link(filename, EXTATTR_NAMESPACE_USER, buf, bufsize);
    if (n >= 0) {
         /* Convert from length-prefixed BSD style to '\0'-suffixed
            Linux style. */
         size_t i = 0;
         while (i < n) {
             unsigned char length = (unsigned char) buf[i];
	     memmove(buf + i, buf + i + 1, length);
	     buf[i + length] = '\0';
	     i += length + 1;
	 }
	 o = Py_BuildValue("s#", buf, (int) n);
    } else {
         o = Py_BuildValue("i", errno);
    }
    free(buf);
#else
    bufsize = 0;
    o = NULL;
    do {
        bufsize += 1024;
        buf = malloc(bufsize);
        if (buf == NULL) {
            Py_INCREF(Py_None);
            return Py_None;
        }
        n = llistxattr(filename, buf, bufsize);

        if (n >= 0)
            o = Py_BuildValue("s#", buf, (int) n);
        else if (n == -1 && errno != ERANGE)
            o = Py_BuildValue("i", errno);
        free(buf);
    } while (o == NULL);
#endif
    return o;
}


static PyObject *
lgetxattr_wrapper(PyObject *self, PyObject *args)
{
    const char *filename;
    const char *attrname;
    size_t bufsize;
    PyObject *o;

    if (!PyArg_ParseTuple(args, "ss", &filename, &attrname))
        return NULL;

    bufsize = 0;
    o = NULL;
    do {
        bufsize += 1024;
        char *buf = malloc(bufsize);
        if (buf == NULL) {
            Py_INCREF(Py_None);
            return Py_None;
        }
#ifdef __FreeBSD__
	int n = extattr_get_link(filename, EXTATTR_NAMESPACE_USER, attrname, buf, bufsize);
#else
        ssize_t n = lgetxattr(filename, attrname, buf, bufsize);
#endif
        if (n >= 0)
            o = Py_BuildValue("s#", buf, (int) n);
        else if (n == -1 && errno != ERANGE)
            o = Py_BuildValue("i", errno);
        free(buf);
    } while (o == NULL);

    return o;
}


static PyObject *
lsetxattr_wrapper(PyObject *self, PyObject *args)
{
    const char *filename;
    const char *name;
    const char *value;
    int size;
    int ret;

    if (!PyArg_ParseTuple(args, "sss#", &filename, &name, &value, &size))
        return NULL;

#ifdef __FreeBSD__
    ret = extattr_set_link(filename, EXTATTR_NAMESPACE_USER, name, value, size);
#else
    ret = lsetxattr(filename, name, value, size, 0);
#endif
    if (ret == -1)
        ret = errno;
    return Py_BuildValue("i", ret);
}


static PyMethodDef methods[] = {
    {"fadvise_dontneed",  fadvise_dontneed, METH_VARARGS,
     "Call posix_fadvise(2) with POSIX_FADV_DONTNEED argument."},
    {"utimensat", utimensat_wrapper, METH_VARARGS,
     "utimensat(2) wrapper."},
    {"lstat", lstat_wrapper, METH_VARARGS,
     "lstat(2) wrapper; arg is filename, returns tuple."},
    {"llistxattr", llistxattr_wrapper, METH_VARARGS,
     "llistxattr(2) wrapper; arg is filename, returns tuple."},
    {"lgetxattr", lgetxattr_wrapper, METH_VARARGS,
     "lgetxattr(2) wrapper; arg is filename, returns tuple."},
    {"lsetxattr", lsetxattr_wrapper, METH_VARARGS,
     "lsetxattr(2) wrapper; arg is filename, returns errno."},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};


PyMODINIT_FUNC
init_obnam(void)
{
    (void) Py_InitModule("_obnam", methods);
}
