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
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "env.h"
#include "data.h"
#include "which.h"

#define wrapper_postfix WRAPPER_POSTFIX

#ifdef __APPLE__
#include <dlfcn.h>
#endif


int main(int argc, char **argv, char **envp) {
    char *original_exe = malloc(strlen(argv[0]) + strlen(wrapper_postfix) + 1);
    sprintf(original_exe, "%s%s", argv[0], wrapper_postfix);

    bool hooked = false;

#ifdef __APPLE__
    // Restore DYLD_INSERT_LIBRARIES stripped by platform binaries up the chain,
    // so that libinterceptor gets into the real tool
    char *libinterceptor = getenv(CLADE_DYLD_INSERT_LIBRARIES_ENV);
    if (libinterceptor)
        setenv("DYLD_INSERT_LIBRARIES", libinterceptor, 0);

    // If libinterceptor is loaded into the wrapper itself, it records the exec below
    hooked = dlsym(RTLD_DEFAULT, "clade_execve") != NULL;
#endif

    // Copy envp, so we can safely modify it later
    // All missing Clade environment variables will be added to "new_envp"
    // from "environ" if they were absent in "evnp"
    char **new_envp = copy_envp((char **)envp);

    /* First case: original executable file was renamed
     * (.clade extension was added to its name)
     * and symlink to the wrapper was added instead.
     */
    if(access(original_exe, F_OK) != -1) {
        // Intercept call only if clade-intercept is working
        if (getenv_from_envp(new_envp, CLADE_INTERCEPT_EXEC_ENV)) {
            char *which = realpath(original_exe, NULL);

            if (!which) {
                fprintf(stderr, "which is empty\n");
                exit(EXIT_FAILURE);
            }

            // strip wrapper_postfix extension
            which[strlen(which) - strlen(wrapper_postfix)] = 0;
            intercept_exec_call(which, (char const *const *)argv, new_envp);
        }

        // First argument must be a valid path, not just a filename
        argv[0] = original_exe;
        // Execute original file
        return execve(original_exe, argv, new_envp);
    } else {
        // Otherwise directory with wrappers is located in the PATH variable
        char *path = strstr(strdup(getenv("PATH")), WHICH_DELIMITER);
        char *which = which_path(basename(argv[0]), path);

        if (!which) {
            fprintf(stderr, "which is empty\n");
            exit(EXIT_FAILURE);
        }

#ifdef __APPLE__
        char *xcode_which = which_xcode(which);
        if (xcode_which)
            which = xcode_which;
#endif

        if (!hooked && getenv_from_envp(new_envp, CLADE_INTERCEPT_EXEC_ENV)) {
            intercept_exec_call(which, (char const *const *)argv, new_envp);
        }

        // First argument must be a valid path, not just a filename
        argv[0] = which;
        return execve(which, argv, new_envp);
    }

    fprintf(stderr, "Something went wrong\n");
    exit(EXIT_FAILURE);
}
