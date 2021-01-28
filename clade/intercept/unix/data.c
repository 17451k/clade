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
#include <unistd.h>

#include "which.h"
#include "env.h"
#include "client.h"
#include "lock.h"

#define DELIMITER "||"

static void expand_newlines(char *dest, const char *src) {
    for (size_t i = 0; i < strlen(src); i++) {
        switch(src[i]) {
            case '\n':
                dest += sprintf(dest, "\\n");
                if (i + 1 < strlen(src) && src[i + 1] == '\r') {
                    i++;
                }
                break;
            case '\r':
                dest += sprintf(dest, "\\n");
                if (i + 1 < strlen(src) && src[i + 1] == '\n') {
                    i++;
                }
                break;

            default:
                *(dest++) = src[i];
        }
    }

    *dest = '\0';
}

// Returned buffer may be up to twice as large as necessary
static char *expand_newlines_alloc(const char *src) {
    char *dest = malloc(2 * strlen(src) + 1);
    expand_newlines(dest, src);
    return dest;
}

static char *prepare_exec_data(const char *path, char const *const argv[]) {
    unsigned args_len = 1, written_len = 0;

    // Concatenate all command-line arguments together using "||" as delimeter.
    for (const char *const *arg = argv; arg && *arg; arg++) {
        // Argument might be replaced by a new large string with escaped newlines
        args_len += 2 * strlen(*arg) + 1;
        // Each separator will require additional bytes
        if ((arg + 1) && *(arg + 1))
            args_len += strlen(DELIMITER);
    }

    // Get current working directory
    const char *cwd = getcwd(NULL, 0);
    if (!cwd) {
        fprintf(stderr, "Couldn't get current working directory");
        exit(EXIT_FAILURE);
    }

    // Sometimes "path" contains incorrect values ("gcc" instead of "/usr/bin/gcc")
    char *correct_path = NULL;
    if (access(path, X_OK)) {
        correct_path = which(path);
    }

    if (!correct_path) {
        correct_path = (char *)path;
    }

    // Allocate memory to store the data + cwd + which + PID (50) + delimeters.
    char *data = malloc(args_len + strlen(cwd) + strlen(DELIMITER) * 3 + 50
                        + strlen(correct_path) + strlen("\n"));

    if (!data) {
        fprintf(stderr, "Couldn't allocate memory\n");
        exit(EXIT_FAILURE);
    }

    char *parent_id = get_parent_id();
    written_len += sprintf(data + written_len, "%s%s%s%s%s%s",
        cwd, DELIMITER,
        parent_id, DELIMITER,
        correct_path, DELIMITER
    );
    free(parent_id);

    for (const char *const *arg = argv; arg && *arg; arg++) {
        char *exp_arg = expand_newlines_alloc(*arg);
        written_len += sprintf(data + written_len, "%s", exp_arg);
        free(exp_arg);

        if ((arg + 1) && *(arg + 1))
            written_len += sprintf(data + written_len, DELIMITER);
    }

    written_len += sprintf(data + written_len, "\n");

    return data;
}

static char *prepare_open_data(const char *path, int flags) {
    // Allocate memory to store the CMD_ID + existence + path + " " and "\n".
    char *data = malloc(sizeof(int) * 3 + strlen("   \n") + strlen(path));

    if (!data) {
        fprintf(stderr, "Couldn't allocate memory\n");
        exit(EXIT_FAILURE);
    }

    int exists = 1;
    if (access(path, F_OK)) {
        exists = 0;
    }

    int cmd_id = get_cmd_id();

    sprintf(data, "%d %d %d %s\n", cmd_id, exists, flags, path);

    return data;
}

static void store_data(const char *data, const char *data_file) {
    FILE *f = fopen(data_file, "a");
    if (!f) {
        fprintf(stderr, "Couldn't open %s file\n", data_file);
        exit(EXIT_FAILURE);
    }

    fprintf(f, "%s", data);
    fclose(f);
}

void intercept_exec_call(const char *path, char const *const argv[]) {
    char *data_file = getenv_or_fail(CLADE_INTERCEPT_EXEC_ENV);

    clade_lock();

    // Data with intercepted command which will be stored
    char *data = prepare_exec_data(path, argv);

    if (getenv(CLADE_PREPROCESS_ENV))
        send_data(data);
    else
        store_data(data, data_file);

    free(data);

    clade_unlock();
}

void intercept_open_call(const char *path, int flags) {
    char *data_file = getenv_or_fail(CLADE_INTERCEPT_OPEN_ENV);

    clade_lock();

    // Data with intercepted command which will be stored
    char *data = prepare_open_data(path, flags);
    store_data(data, data_file);
    free(data);

    clade_unlock();
}
