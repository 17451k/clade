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

#include <libgen.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "env.h"
#include "data.h"
#include "which.h"

#define wrapper_postfix ".clade"


int main(int argc, char **argv, char **envp) {
    char *original_exe = malloc(strlen(argv[0]) + strlen(wrapper_postfix) + 1);
    sprintf(original_exe, "%s%s", argv[0], wrapper_postfix);

    /* First case: original executable file was renamed
     * (.clade extension was added to its name)
     * and symlink to the wrapper was added instead.
     */
    if(access(original_exe, F_OK) != -1) {
        // Intercept call only if clade-intercept is working
        if (getenv(CLADE_INTERCEPT_EXEC_ENV)) {
            char *which = realpath(original_exe, NULL);

            if (!which) {
                fprintf(stderr, "which is empty\n");
                exit(EXIT_FAILURE);
            }

            // strip wrapper_postfix extension
            which[strlen(which) - strlen(wrapper_postfix)] = 0;
            intercept_exec_call(which, (char const *const *)argv);
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

        if (getenv(CLADE_INTERCEPT_EXEC_ENV)) {
            intercept_exec_call(which, (char const *const *)argv);
        }

        // First argument must be a valid path, not just a filename
        argv[0] = which;
        return execve(which, argv, envp);
    }

    fprintf(stderr, "Something went wrong\n");
    exit(EXIT_FAILURE);
}
