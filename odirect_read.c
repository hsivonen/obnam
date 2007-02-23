/*
 * odirect_read.c -- copy specified file to stdout, using O_DIRECT
 *
 * Copyright (C) 2006  Lars Wirzenius <liw@iki.fi>
 * 
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
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


#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <sys/types.h>
#include <sys/stat.h>
#include <sys/vfs.h>
#include <fcntl.h>
#include <unistd.h>


int main(int argc, char **argv)
{
    int fd;
    ssize_t num_read;
    ssize_t num_written;
    void *buf;
    int error;
    struct statfs sfs;
    size_t buf_size;
    
    if (argc != 2) {
        fprintf(stderr, "Usage: %s filename\n", argv[0]);
        fprintf(stderr, "Note: exactly one argument, this ain't cat\n");
        return EXIT_FAILURE;
    }
    
    fd = open(argv[1], O_RDONLY | O_DIRECT | O_LARGEFILE);
    if (fd == -1) {
        /* 
         * Let's try this again without O_DIRECT, just in case we're trying
         * to read a device file, or a network filesystem, or something
         * else that won't work with O_DIRECT.
         */
      open_without_o_direct:
        fd = open(argv[1], O_RDONLY | O_LARGEFILE);
    }
    if (fd == -1) {
        fprintf(stderr, "%s: ERROR: Trying to open %s: %d: %s\n",
                argv[0], argv[1], errno, strerror(errno));
        return EXIT_FAILURE;
    }
    
    /*
     * Linux 2.4 requires the buffer to be aligned at the filesystem
     * block size, the transfer size needs to be a multiple of the block
     * size, and also for the file offset to be a multiple of the
     * filesystem block size. We allocate a block that is a multiple of
     * said size and that should take care of things.
     */
    
    if (fstatfs(fd, &sfs) == -1) {
        fprintf(stderr, "%s: ERROR: Trying to statfs %s: %d: %s\n",
                argv[1], errno, strerror(errno));
        return EXIT_FAILURE;
    }
    
    /* 
     * In some quick testing, buffers much bigger than this did not make
     * things happen faster.
     */
    buf_size = sfs.f_bsize * 32;

    error = posix_memalign(&buf, sfs.f_bsize, buf_size);
    if (error != 0) {
        fprintf(stderr, "%s: ERROR: Allocating aligned memory: %d: %s\n",
                argv[0], error, strerror(error));
        return EXIT_FAILURE;
    }
    
    ssize_t total = 0;
    for (;;) {
        num_read = read(fd, buf, buf_size);

        if (num_read == -1 && errno == EINTR)
            continue;
            
        if (num_read == -1 && errno == EINVAL && total == 0) {
            /* 
             * For some reason, O_DIRECT doesn't seem to work under 2.4
             * kernels anyway, at least not always. If so, it fails at
             * the first read, so we restart from the beginning, without
             * O_DIRECT.
             */
            (void) close(fd);
            goto open_without_o_direct;
        }

        if (num_read == -1) {
            fprintf(stderr, "%s: ERROR: Reading %s: %d: %s\n",
                    argv[0], argv[1], errno, strerror(errno));
            return EXIT_FAILURE;
        }

        if (num_read == 0)
            break;

        total += num_read;

        do {
            num_written = write(1, buf, num_read);
        } while (num_written == -1 && errno == EINTR);

        if (num_written == -1) {
            fprintf(stderr, "%s: ERROR: Writing to stdout: %d: %s\n",
                    argv[0], errno, strerror(errno));
            return EXIT_FAILURE;
        }
    }
    
    if (close(fd) == -1) {
        fprintf(stderr, "%s: ERROR: Closing %s: %d: %s\n",
                argv[0], argv[1], errno, strerror(errno));
        return EXIT_FAILURE;
    }
    
    return 0;
}
