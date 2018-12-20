/*
 * Copyright (c) 2018 ISP RAS (http://www.ispras.ru)
 * Ivannikov Institute for System Programming of the Russian Academy of Sciences
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#ifndef CLADE_COMPAT_H
#define CLADE_COMPAT_H

#ifdef _WIN32

#include <windows.h>
#include <process.h>
#include <direct.h>
#include <io.h>

#define strdup(str) _strdup(str)
#define setenv(name, value, overwrite) _putenv_s (name, value)
#define getcwd(buffer, maxlen) _getcwd(buffer, maxlen)
#define access(path, mode) _access(path, mode)
#define execve(cmdname, argv, envp) _execve(cmdname, argv, envp)

// execute permission is unsupported in Windows, use R_OK instead.
#define R_OK 4
#define X_OK R_OK
#define F_OK 0

static inline char *basename(char *path) {
    char *fname = malloc(strlen(path));
    char *ext = malloc(strlen(path));

    _splitpath(path, NULL, NULL, fname, ext);
    sprintf(fname, "%s%s", fname, ext);
    return fname;
}

#else

#include <unistd.h>
#include <sys/file.h>
#include <libgen.h>

#endif

#endif /* CLADE_COMPAT_H */
