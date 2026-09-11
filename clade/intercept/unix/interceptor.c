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
#include <string.h>
#include <unistd.h>
#include <stdarg.h>
#include <fcntl.h>
#include <stdlib.h>
#include <stdio.h>

#define __USE_GNU
#include <dlfcn.h>

#include "data.h"
#include "env.h"
#include "which.h"

#ifdef __APPLE__
#include <libgen.h>

// Modern dyld ignores DYLD_FORCE_FLAT_NAMESPACE, so redefining a libSystem
// symbol has no effect: hooks must be registered in the __interpose section.
#define HOOK(name) clade_##name
#define DYLD_INTERPOSE(replacement, replacee) \
    __attribute__((used)) static struct { const void *replacement; const void *replacee; } \
    interpose_##replacee __attribute__((section("__DATA,__interpose"))) = { \
        (const void *)(unsigned long)&replacement, (const void *)(unsigned long)&replacee };

// Calls from the interposing library itself are not interposed, so the
// original symbol is called directly: dlsym() from a hook that runs during
// libSystem initialization (open() from libxpc) is prohibitively slow.
#define real(name) (&name)
#define check_dlerror()

static char *wrapper_path;

// On macOS libinterceptor is injected by wrappers (see wrapper.c). An exec of
// a wrapper is not a command: the wrapper records it when it execs the real
// tool. An exec of a renamed original (Wrapper.wrap_list) by the wrapper is
// already recorded by it under the original name.
static bool is_wrapper(const char *path) {
    size_t len = strlen(path), postfix_len = strlen(WRAPPER_POSTFIX);

    if (len > postfix_len && strcmp(path + len - postfix_len, WRAPPER_POSTFIX) == 0)
        return true;

    char *real = realpath(path, NULL);
    bool res = real && wrapper_path && strcmp(real, wrapper_path) == 0;
    free(real);
    return res;
}

// Bypass /usr/bin shims (see which_xcode) so that libinterceptor stays injected.
// CommandLineTools gcc and g++ are launchers executing "xcrun <tool> ...", and
// xcrun is a platform binary too: run the tool directly, as xcrun would.
static void resolve_shim(const char **path, char *const **argv) {
    char *xcode_path = getenv(CLADE_XCODE_PATH_ENV);

    if (xcode_path && (strcmp(*path, "/usr/bin/xcrun") == 0 || strcmp(*path, "xcrun") == 0)
        && (*argv)[0] && (*argv)[1] && (*argv)[1][0] != '-') {
        char *tool = which_path((*argv)[1], xcode_path);

        if (tool) {
            *path = tool;
            *argv += 1;
            return;
        }
    }

    xcode_path = which_xcode(*path);
    if (xcode_path)
        *path = xcode_path;
}
#else
#define resolve_shim(path, argv)
#define HOOK(name) name
#define real(name) dlsym(RTLD_NEXT, #name)
#define is_wrapper(path) false

static void check_dlerror(void) {
    char *error = dlerror();

    if (error) {
        fprintf(stderr, "%s\n", error);
        exit(1);
    }
}
#endif

static bool intercepted;

pid_t HOOK(vfork)() {
    // Child processes that are created by vfork() can mess up data structures of the parent process.
    // libinterceptor changes some environment variables, and due to vfork() it can affect its parent process.
    // It breaks some things here, so to fix it we decided to replace vfork() call by fork().
    return fork();
}

extern char **environ;
char **clade_environ;

void on_load(void) __attribute__((constructor));

void on_load(void) {
    if (!clade_environ)
        clade_environ = copy_envp(environ);

#ifdef __APPLE__
    Dl_info info;
    if (dladdr((void *)on_load, &info)) {
        char *dir = dirname(strdup(info.dli_fname));
        char *path = malloc(strlen(dir) + sizeof("/wrapper"));
        sprintf(path, "%s/wrapper", dir);
        wrapper_path = realpath(path, NULL);
        free(path);
    }
#endif
}

// This wrapper will be executed instead of original execve() by using LD_PRELOAD ability.
int HOOK(execve)(const char *path, char *const argv[], char *const envp[]) {
    int (*execve_real)(const char *, char *const *, char *const *) = real(execve);

    check_dlerror();

    // Add Clade environment variables from clade_environ to environ if they were absent
    if (!getenv(CLADE_INTERCEPT_EXEC_ENV)) {
        update_environ(clade_environ, false);
    }

    if (!intercepted && getenv(CLADE_INTERCEPT_EXEC_ENV) && !is_wrapper(path)) {
        char *const *args = argv;
        resolve_shim(&path, &args);

        // Copy envp, so we can safely modify it later
        // All missing Clade environment variables will be added to "new_envp"
        // from "environ" if they were absent in "evnp"
        char **new_envp = copy_envp((char **)envp);

        // Store information about intercepted call
        intercept_exec_call(path, (char const *const *)args, new_envp);
        intercepted = true;

        return execve_real(path, args, (char *const *restrict)new_envp);
    }

    // Execute original execve()
    return execve_real(path, argv, envp);
}

int HOOK(execvp)(const char *filename, char *const argv[]) {
    int (*execvp_real)(const char *, char *const *) = real(execvp);

    check_dlerror();

    // Add Clade environment variables from clade_environ to environ if they were absent
    if (!getenv(CLADE_INTERCEPT_EXEC_ENV)) {
        update_environ(clade_environ, false);
    }

    if (!intercepted && getenv(CLADE_INTERCEPT_EXEC_ENV) && !is_wrapper(filename)) {
        resolve_shim(&filename, &argv);

        // Copy environ, so we can safely modify it later
        char **new_envp = copy_envp((char **)environ);

        intercept_exec_call(filename, (char const *const *)argv, (char **)new_envp);
        // DO NOT change value of intercepted to TRUE here

        // intercept_exec_call changed some environment values in new_envp, which now should be added back to environ
        update_environ(new_envp, true);
    }

    return execvp_real(filename, argv);
}

int HOOK(execv)(const char *filename, char *const argv[]) {
    int (*execv_real)(const char *, char *const *) = real(execv);

    check_dlerror();

    // Add Clade environment variables from clade_environ to environ if they were absent
    if (!getenv(CLADE_INTERCEPT_EXEC_ENV)) {
        update_environ(clade_environ, false);
    }

    // DO NOT check if (! intercepted) here: it will result in command loss
    // Also DO NOT change value of intercepted to TRUE for the same reason
    if (getenv(CLADE_INTERCEPT_EXEC_ENV) && !is_wrapper(filename)) {
        resolve_shim(&filename, &argv);

        // Copy environ, so we can safely modify it later
        char **new_envp = copy_envp((char **)environ);

        intercept_exec_call(filename, (char const *const *)argv, (char **)new_envp);

        // intercept_exec_call changed some environment values in new_envp, which now should be added back to environ
        update_environ(new_envp, true);
    }
    // BUT we need to change it for macOS to avoid duplicating commands
    #ifdef __APPLE__
    intercepted = true;
    #endif

    return execv_real(filename, argv);
}

int HOOK(posix_spawn)(pid_t *restrict pid, const char *restrict path, const posix_spawn_file_actions_t *file_actions,
                const posix_spawnattr_t *restrict attrp, char *const argv[restrict], char *const envp[restrict])
{
    int (*posix_spawn_real)(pid_t *restrict, const char *restrict, const posix_spawn_file_actions_t *,
                const posix_spawnattr_t *restrict, char *const *restrict, char *const *restrict) = real(posix_spawn);

    check_dlerror();

    // Add Clade environment variables from clade_environ to environ if they were absent
    if (!getenv(CLADE_INTERCEPT_EXEC_ENV)) {
        update_environ(clade_environ, false);
    }

    // DO NOT check if (! intercepted) here: it will result in command loss
    if ((access(path, F_OK ) != -1) && getenv(CLADE_INTERCEPT_EXEC_ENV) && argv && !is_wrapper(path)) {
        const char *spawn_path = path;
        char *const *args = argv;
        resolve_shim(&spawn_path, &args);

        // Copy envp, so we can safely modify it later
        // All missing Clade environment variables will be added to "new_envp"
        // from "environ" if they were absent in "evnp"
        char **new_envp = copy_envp((char **)envp);

        intercept_exec_call(spawn_path, (char const *const *)args, new_envp);
        intercepted = true;

        return posix_spawn_real(pid, spawn_path, file_actions, attrp, args, (char *const *restrict)new_envp);
    }

    return posix_spawn_real(pid, path, file_actions, attrp, argv, envp);
}

int HOOK(open)(const char *pathname, int flags, ...) {
    int (*open_real)(const char *, int, ...) = real(open);

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

#ifdef __APPLE__
DYLD_INTERPOSE(clade_vfork, vfork)
DYLD_INTERPOSE(clade_execve, execve)
DYLD_INTERPOSE(clade_execvp, execvp)
DYLD_INTERPOSE(clade_execv, execv)
DYLD_INTERPOSE(clade_posix_spawn, posix_spawn)
DYLD_INTERPOSE(clade_open, open)
#else
int open64(const char *pathname, int flags, ...) {
    int (*open_real)(const char *, int, ...) = real(open64);

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
#endif
