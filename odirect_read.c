/*
 * odirect_read.c -- copy specified file to stdout, using O_DIRECT
 */


#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>


enum { BUFFER_SIZE = 64 * 1024 };


int main(int argc, char **argv)
{
    int fd;
    ssize_t num_read;
    ssize_t num_written;
    void *buf;
    int error;
    
    if (argc != 2) {
        fprintf(stderr, "Usage: %s filename\n", argv[0]);
        fprintf(stderr, "Note: exactly one argument, this ain't cat\n");
        return EXIT_FAILURE;
    }
    
    fd = open(argv[1], O_RDONLY | O_DIRECT);
    if (fd == -1) {
        fprintf(stderr, "%s: ERROR: Trying to open %s: %d: %s\n",
                argv[0], argv[1], errno, strerror(errno));
        return EXIT_FAILURE;
    }
    
    error = posix_memalign(&buf, 512, BUFFER_SIZE);
    if (error != 0) {
        fprintf(stderr, "%s: ERROR: Allocating aligned memory: %d: %s\n",
                argv[0], error, strerror(error));
        return EXIT_FAILURE;
    }
    
    for (;;) {
        num_read = read(fd, buf, BUFFER_SIZE);

        if (num_read == -1 && errno == EINTR)
            continue;

        if (num_read == -1) {
            fprintf(stderr, "%s: ERROR: Reading %s: %d: %s\n",
                    argv[0], argv[1], errno, strerror(errno));
            return EXIT_FAILURE;
        }

        if (num_read == 0)
            break;

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
