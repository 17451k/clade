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

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "compat.h"
#include "data.h"
#include "which.h"

#define wrapper_postfix ".clade.exe"

#ifdef _WIN32

static char **wrap_in_quotes(char **argv) {
    int argv_len;
    for(argv_len = 0; argv[argv_len] != NULL; argv_len++);

    char **copy = malloc((argv_len + 1) * sizeof(char *));

    int i;
    for (i = 0; i < argv_len; i++) {
        // Wrap only arguments that contain spaces
        if (strchr(argv[i], ' ')) {
            copy[i] = malloc(strlen(argv[i]) + 2);
            sprintf(copy[i], "\"%s\"", argv[i]);
        }
        else {
            copy[i] = argv[i];
        }
    }

    copy[i] = 0;
    return copy;
}

int main(int argc, char **argv) {
    char *original_exe = malloc(strlen(argv[0]) + strlen(wrapper_postfix) + 1);
    sprintf(original_exe, "%s%s", argv[0], wrapper_postfix);

    if(access(original_exe, F_OK) != -1) {
        // Intercept call only if clade-intercept is working
        if (getenv("CLADE_INTERCEPT")) {
            char *file_ext;
            char which[MAX_PATH];
            int r = GetFullPathName(original_exe, MAX_PATH, which, &file_ext);

            if (!r) {
                fprintf(stderr, "Couldn't get full path to the original exe file\n");
                exit(EXIT_FAILURE);
            }

            which[strlen(which) - strlen(wrapper_postfix)] = 0;
            intercept_call(which, (char const *const *)argv);
        }

        argv[0] = original_exe;
        return execv(original_exe, wrap_in_quotes(argv));
    } else {
        char *path = strstr(strdup(getenv("PATH")), WHICH_DELIMITER);
        char *which = which_path(basename(argv[0]), path);

        if (which) {
            if (getenv("CLADE_INTERCEPT"))
                intercept_call(which, (char const *const *)argv);

            argv[0] = which;
            return execv(which, wrap_in_quotes(argv));
        } else {
            // Otherwise
            char wrapper_name[MAX_PATH];
            int r = GetModuleFileName(NULL, wrapper_name, MAX_PATH);

            if (!r) {
                fprintf(stderr, "Couldn't get module name\n");
                exit(EXIT_FAILURE);
            }

            if (getenv("CLADE_INTERCEPT"))
                intercept_call(wrapper_name, (char const *const *)argv);

            sprintf(wrapper_name, "%s%s", wrapper_name, wrapper_postfix);
            argv[0] = wrapper_name;
            return execv(wrapper_name, wrap_in_quotes(argv));
        }
    }

    fprintf(stderr, "Something went wrong\n");
    exit(EXIT_FAILURE);
}

#else

int main(int argc, char **argv, char **envp) {
    char *original_exe = malloc(strlen(argv[0]) + strlen(wrapper_postfix) + 1);
    sprintf(original_exe, "%s%s", argv[0], wrapper_postfix);

    /* First case: original executable file was renamed
     * (.clade.exe extension was added to its name)
     * and symlink to the wrapper was added instead.
     */
    if(access(original_exe, F_OK) != -1) {
        // Intercept call only if clade-intercept is working
        if (getenv("CLADE_INTERCEPT")) {
            char *which = realpath(original_exe, NULL);

            if (!which) {
                fprintf(stderr, "which is empty\n");
                exit(EXIT_FAILURE);
            }

            // strip wrapper_postfix extension
            which[strlen(which) - strlen(wrapper_postfix)] = 0;
            intercept_call(which, (char const *const *)argv);
        }

        // First argument must be a valid path, not just a filename
        argv[0] = original_exe;
        // Execute original file
        return execve(original_exe, argv, envp);
    } else {
        // Otherwise directory with wrappers is located in the PATH variable
        char *path = strstr(strdup(getenv("PATH")), WHICH_DELIMITER);
        char *which = which_path(basename(argv[0]), path);

        if (!which) {
            fprintf(stderr, "which is empty\n");
            exit(EXIT_FAILURE);
        }

        intercept_call(which, (char const *const *)argv);

        // First argument must be a valid path, not just a filename
        argv[0] = which;
        return execve(which, argv, envp);
    }

    fprintf(stderr, "Something went wrong\n");
    exit(EXIT_FAILURE);
}

#endif /* _WIN32 */
