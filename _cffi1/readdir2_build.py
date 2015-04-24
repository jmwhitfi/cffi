from cffi1 import FFI
from recompiler import recompile

ffi = FFI()
ffi.cdef("""

    typedef ... DIR;

    struct dirent {
        unsigned char  d_type;      /* type of file; not supported
                                       by all file system types */
        char           d_name[...]; /* filename */
        ...;
    };

    int readdir_r(DIR *dirp, struct dirent *entry, struct dirent **result);
    int openat(int dirfd, const char *pathname, int flags);
    DIR *fdopendir(int fd);
    int closedir(DIR *dirp);

    static const int DT_DIR;

""")
recompile(ffi, "_readdir2", """
#ifndef _ATFILE_SOURCE
#  define _ATFILE_SOURCE
#endif
#ifndef _BSD_SOURCE
#  define _BSD_SOURCE
#endif
#include <fcntl.h>
#include <sys/types.h>
#include <dirent.h>
""")
