/*
 * _obnammodule.c -- Python extensions for Obna
 *
 * Copyright (C) 2008, 2009  Lars Wirzenius <liw@liw.fi>
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


#include <Python.h>


#ifndef _XOPEN_SOURCE
#define _XOPEN_SOURCE 600
#endif
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <sys/stat.h>


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
lutimes_wrapper(PyObject *self, PyObject *args)
{
    int ret;
    const char *filename;
    struct timeval tv[2];

    if (!PyArg_ParseTuple(args, "sllll", 
                          &filename, 
                          &tv[0].tv_sec,
                          &tv[0].tv_usec,
                          &tv[1].tv_sec,
                          &tv[1].tv_usec))
        return NULL;

    ret = lutimes(filename, tv);
    if (ret == -1)
        ret = errno;
    return Py_BuildValue("i", ret);
}


static PyMethodDef methods[] = {
    {"fadvise_dontneed",  fadvise_dontneed, METH_VARARGS, 
     "Call posix_fadvise(2) with POSIX_FADV_DONTNEED argument."},
    {"lutimes", lutimes_wrapper, METH_VARARGS,
     "lutimes(2) wrapper; args are filename, atime, and mtime."},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};


PyMODINIT_FUNC
init_obnam(void)
{
    (void) Py_InitModule("_obnam", methods);
}
