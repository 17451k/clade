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

#include <sys/file.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "which.h"

#define DELIMITER "||"

static void expand_newlines(char* dest, const char* src) {
    for (int i = 0; i < strlen(src); i++) {
        switch(src[i]) {
            case '\n':
                dest += sprintf(dest, "\\n");
                break;
            default:
                *(dest++) = src[i];
        }
    }

    *dest = '\0';
}

// Returned buffer may be up to twice as large as necessary
static char* expand_newlines_alloc(const char* src) {
    char* dest = malloc(2 * strlen(src) + 1);
    expand_newlines(dest, src);
    return dest;
}

static char *prepare_data(const char *path, char const *const argv[]) {
    unsigned args_len = 1, written_len = 0;

    // Concatenate all command-line arguments together using "||" as delimeter.
    for (const char *const *arg = argv; arg && *arg; arg++) {
        // Argument might be replaced by a new large string with escaped newlines
        args_len += 2 * strlen(*arg) + 1;
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

    // Sometimes "path" contains incorrect values ("gcc" instead of "/usr/bin/gcc")
    char *correct_path = NULL;
    if (path == argv[0]) {
        correct_path = which(path);
    }

    if (!correct_path) {
        correct_path = (char *)path;
    }

    // Allocate memory to store the data + cwd + delimeters
    char *data = malloc(args_len + strlen(cwd) + strlen(DELIMITER)
                        + strlen(correct_path) + strlen(DELIMITER) + strlen("\n"));

    if (!data) {
        fprintf(stderr, "Couldn't allocate memory\n");
        exit(EXIT_FAILURE);
    }

    written_len += sprintf(data + written_len, "%s", cwd);
    written_len += sprintf(data + written_len, DELIMITER);

    written_len += sprintf(data + written_len, "%s", correct_path);
    written_len += sprintf(data + written_len, DELIMITER);

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

static void store_data(char *data, char *data_file) {
    FILE *f = fopen(data_file, "a");
    if (!f) {
        fprintf(stderr, "Couldn't open %s file\n", data_file);
        exit(EXIT_FAILURE);
    }

    flock(fileno(f), LOCK_EX);
    fprintf(f, "%s", data);

    fclose(f);
    flock(fileno(f), LOCK_UN);
}

void intercept_call(const char *path, char const *const argv[]) {
    char *data_file = getenv("CLADE_INTERCEPT");

    if (!data_file) {
        fprintf(stderr, "Environment is not prepared: CLADE_INTERCEPT is not specified\n");
        exit(EXIT_FAILURE);
    }

    // Data with intercepted command which will be stored
    char *data = prepare_data(path, argv);
    store_data(data, data_file);
    free(data);
}

void intercept_call_fallback(const char *path, char const *const argv[]) {
    char *data_file = getenv("CLADE_INTERCEPT_FALLBACK");

    if (!data_file) {
        fprintf(stderr, "Environment is not prepared: CLADE_INTERCEPT_FALLBACK is not specified\n");
        exit(EXIT_FAILURE);
    }

    // Data with intercepted command which will be stored
    char *data = prepare_data(path, argv);
    store_data(data, data_file);
    free(data);
}
