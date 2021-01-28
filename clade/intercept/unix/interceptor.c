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

#include <spawn.h>
#include <stdbool.h>
#include <unistd.h>
#include <stdarg.h>
#include <fcntl.h>
#include <stdlib.h>

#define __USE_GNU
#include <dlfcn.h>

#include "data.h"
#include "env.h"

static bool intercepted;

pid_t vfork() {
    // Child processes that are created by vfork() can mess up data structures of the parent process.
    // libinterceptor changes some environment variables, and due to vfork() it can affect its parent process.
    // It breaks some things here, so to fix it we decided to replace vfork() call by fork().
    return fork();
}

// This wrapper will be executed instead of original execve() by using LD_PRELOAD ability.
int execve(const char *path, char *const argv[], char *const envp[]) {
    int (*execve_real)(const char *, char *const *, char *const *) = dlsym(RTLD_NEXT, "execve");

    if (!intercepted && getenv(CLADE_INTERCEPT_EXEC_ENV)) {
        // Extract some data from envp
        update_environ((char **)envp);
        // Store information about intercepted call
        intercept_exec_call(path, (char const *const *)argv);
        intercepted = true;

        // Put updated data back to envp
        char **new_envp = update_envp((char **)envp);
        return execve_real(path, argv, (char *const *restrict)new_envp);
    }

    // Execute original execve()
    return execve_real(path, argv, envp);
}

int execvp(const char *filename, char *const argv[]) {
    int (*execvp_real)(const char *, char *const *) = dlsym(RTLD_NEXT, "execvp");

    if (!intercepted && getenv(CLADE_INTERCEPT_EXEC_ENV)) {
        intercept_exec_call(filename, (char const *const *)argv);
        // DO NOT change value of intercepted to TRUE here
    }

    return execvp_real(filename, argv);
}

int execv(const char *filename, char *const argv[]) {
    int (*execv_real)(const char *, char *const *) = dlsym(RTLD_NEXT, "execv");

    // DO NOT check if (! intercepted) here: it will result in command loss
    // Also DO NOT change value of intercepted to TRUE for the same reason
    if (getenv(CLADE_INTERCEPT_EXEC_ENV)) {
        intercept_exec_call(filename, (char const *const *)argv);
    }
    // BUT we need to change it for macOS to avoid duplicating commands
    #ifdef __APPLE__
    intercepted = true;
    #endif

    return execv_real(filename, argv);
}

int posix_spawn(pid_t *restrict pid, const char *restrict path, const posix_spawn_file_actions_t *file_actions,
                const posix_spawnattr_t *restrict attrp, char *const argv[restrict], char *const envp[restrict])
{
    int (*posix_spawn_real)(pid_t *restrict, const char *restrict, const posix_spawn_file_actions_t *,
                const posix_spawnattr_t *restrict, char *const *restrict, char *const *restrict) = dlsym(RTLD_NEXT, "posix_spawn");

    // DO NOT check if (! intercepted) here: it will result in command loss
    if ((access(path, F_OK ) != -1) && getenv(CLADE_INTERCEPT_EXEC_ENV) && argv) {
        update_environ((char **)envp);
        intercept_exec_call(path, (char const *const *)argv);
        intercepted = true;

        char **new_envp = update_envp((char **)envp);
        return posix_spawn_real(pid, path, file_actions, attrp, argv, (char *const *restrict)new_envp);
    }

    return posix_spawn_real(pid, path, file_actions, attrp, argv, envp);
}

int open(const char *pathname, int flags, ...) {
    int (*open_real)(const char *, int, ...) = dlsym(RTLD_NEXT, "open");

    if (getenv(CLADE_INTERCEPT_OPEN_ENV)) {
        intercept_open_call(pathname, flags);
    }

    // If O_CREAT is used to create a file, the file access mode must be given.
    if (flags & O_CREAT) {
        va_list args;
        va_start(args, flags);
        mode_t mode = va_arg(args, int);
        va_end(args);
        return open_real(pathname, flags, mode);
    } else {
        return open_real(pathname, flags);
    }
}


int open64(const char *pathname, int flags, ...) {
    int (*open_real)(const char *, int, ...) = dlsym(RTLD_NEXT, "open64");

    if (getenv(CLADE_INTERCEPT_OPEN_ENV)) {
        intercept_open_call(pathname, flags);
    }

    // If O_CREAT is used to create a file, the file access mode must be given.
    if (flags & O_CREAT) {
        va_list args;
        va_start(args, flags);
        mode_t mode = va_arg(args, int);
        va_end(args);
        return open_real(pathname, flags, mode);
    } else {
        return open_real(pathname, flags);
    }
}
