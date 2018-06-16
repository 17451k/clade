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
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define __USE_GNU
#include <dlfcn.h>

static void intercept_call(const char *path, char const *const argv[]);
static char *prepare_data(const char *path, char const *const argv[]);
static void store_data(char *msg);

static bool intercepted;

// This wrapper will be executed instead of original execve() by using LD_PRELOAD ability.
int execve(const char *path, char *const argv[], char *const envp[]) {
    int (*execve_real)(const char *, char *const *, char *const *) = dlsym(RTLD_NEXT, "execve");

    if (! intercepted) {
        // Store information about intercepted call
        intercept_call(path, (char const *const *)argv);
        intercepted = true;
    }

    // Execute original execve()
    return execve_real(path, argv, envp);
}

int execvp(const char *filename, char *const argv[]) {
    int (*execvp_real)(const char *, char *const *) = dlsym(RTLD_NEXT, "execvp");

    if (! intercepted) {
        intercept_call(filename, (char const *const *)argv);
        intercepted = true;
    }

    return execvp_real(filename, argv);
}

int execv(const char *filename, char *const argv[]) {
    int (*execv_real)(const char *, char *const *) = dlsym(RTLD_NEXT, "execv");

    if (! intercepted) {
        intercept_call(filename, (char const *const *)argv);
        intercepted = true;
    }

    return execv_real(filename, argv);
}

int posix_spawn(pid_t *restrict pid, const char *restrict path, const posix_spawn_file_actions_t *file_actions,
                const posix_spawnattr_t *restrict attrp, char *const argv[restrict], char *const envp[restrict])
{
    int (*posix_spawn_real)(pid_t *restrict, const char *restrict, const posix_spawn_file_actions_t *,
                const posix_spawnattr_t *restrict, char *const *, char *const *) = dlsym(RTLD_NEXT, "posix_spawn");

    if (! intercepted) {
        intercept_call(path, (char const *const *)argv);
        intercepted = true;
    }

    return posix_spawn_real(pid, path, file_actions, attrp, argv, envp);
}

static void intercept_call(const char *path, char const *const argv[]) {
    // TODO: Do we need to use mutex here?
    // Data with intercepted command which will be stored
    char *data = prepare_data(path, argv);
    store_data(data);
    free(data);
}

static char *prepare_data(const char *path, char const *const argv[]) {
    unsigned args_len = 1, written_len = 0;

    // Concatenate all command-line arguments together using "||" as separator.
    for (const char *const *arg = argv; arg && *arg; arg++) {
        args_len += strlen(*arg);
        // Each separator will require 2 additional bytes
        if ((arg + 1) && *(arg + 1))
            args_len += 2;
    }

    // Get current working directory
    const char *cwd = getcwd(NULL, 0);
    if (!cwd) {
        fprintf(stderr, "Couldn't get current working directory");
        exit(EXIT_FAILURE);
    }

    // Allocate memory to store the data + cwd + separators
    char *data = malloc(args_len + strlen(cwd) + strlen("||") + strlen(path) + strlen("||") + strlen("\n"));

    if (!data) {
        fprintf(stderr, "Couldn't allocate memory\n");
        exit(EXIT_FAILURE);
    }

    written_len += sprintf(data + written_len, "%s", cwd);
    written_len += sprintf(data + written_len, "||");

    written_len += sprintf(data + written_len, "%s", path);
    written_len += sprintf(data + written_len, "||");

    for (const char *const *arg = argv; arg && *arg; arg++) {
        written_len += sprintf(data + written_len, "%s", *arg);
        if ((arg + 1) && *(arg + 1))
            written_len += sprintf(data + written_len, "||");
    }

    written_len += sprintf(data + written_len, "\n");

    return data;
}

static void store_data(char *data) {
    char* data_file = getenv("CLADE_INTERCEPT");

    if (!data_file) {
        fprintf(stderr, "Environment is not prepared: CLADE_INTERCEPT is not specified\n");
        exit(EXIT_FAILURE);
    }

    FILE *f = fopen (data_file, "a");
    if (!f) {
        fprintf(stderr, "Couldn't open %s file\n", data_file);
        exit(EXIT_FAILURE);
    }

    fprintf (f, "%s", data);
    fclose (f);
}
