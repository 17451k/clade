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

#include "data.h"
#include "which.h"

int main(int argc, char **argv, char **envp) {
    char *path = strstr(strdup(getenv("PATH")), WHICH_DELIMITER);
    char *which = which_path(basename(argv[0]), path);

    if (!which)
        return -1;

    intercept_call(which, (char const *const *)argv);

    // First argument must be a valid path, not just a filename
    argv[0] = which;
    return execve(which, argv, envp);
}
