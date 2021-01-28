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
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

#include "env.h"

#define ARRAY_SIZE(x) (sizeof(x) / sizeof((x)[0]))

// Environment variables that must be passed to new process
// (only if defined in its parent process)
char *clade_envs[] = {
    CLADE_INTERCEPT_OPEN_ENV,
    CLADE_INTERCEPT_EXEC_ENV,
    CLADE_ID_FILE_ENV,
    CLADE_PARENT_ID_ENV,
    CLADE_UNIX_ADDRESS_ENV,
    CLADE_INET_HOST_ENV,
    CLADE_INET_PORT_ENV,
    CLADE_PREPROCESS_ENV,
    "LD_PRELOAD",
    "LD_LIBRARY_PATH",
    "DYLD_INSERT_LIBRARIES",
    "DYLD_FORCE_FLAT_NAMESPACE",
};
const size_t clade_envs_len = ARRAY_SIZE(clade_envs);

static int get_envp_len(char **envp) {
    int i = 0;
    while(envp[i] != NULL) { i++; }
    return i;
}

static int find_key_index(char **envp, const char* key) {
    size_t key_len = strlen(key);
    int envp_len = get_envp_len(envp);

    int i;
    for (i = 0; i < envp_len; i++) {
        if (strncmp(envp[i], key, key_len) == 0 && (strlen(envp[i]) > key_len) && (envp[i][key_len]) == '=') {
            break;
        }
    }

    if (i < envp_len) {
        return i;
    }

    return -1;
}

static char* construct_envp_entry(const char *key, const char *value) {
    size_t entry_len = strlen(key) + strlen(value) + 2;
    char *new_entry = malloc(entry_len);

    snprintf(new_entry, entry_len, "%s=%s", key, value);

    return new_entry;
}

static char **copy_envp(char **envp) {
    int envp_len = get_envp_len(envp);
    char **copy = malloc((envp_len + clade_envs_len + 1) * sizeof(char *));

    int i;
    for (i = 0; i < envp_len; i++) {
        copy[i] = strdup(envp[i]);
    }

    // Add Clade environment variables to "copy" if they were absent in "evnp"
    for (int j = 0; j < clade_envs_len; j++) {
        if (getenv(clade_envs[j]) && find_key_index(envp, clade_envs[j]) == -1) {
            copy[i++] = construct_envp_entry(clade_envs[j], getenv(clade_envs[j]));
        }
    }

    copy[i] = 0;
    return copy;
}

char **update_envp(char **input_envp) {
    if (!input_envp)
        return input_envp;

    char *value = getenv(CLADE_PARENT_ID_ENV);
    char *new_entry = construct_envp_entry(CLADE_PARENT_ID_ENV, value);

    char **envp = copy_envp(input_envp);
    int i = find_key_index(envp, CLADE_PARENT_ID_ENV);

    if (i != -1) {
        free(envp[i]);
        envp[i] = new_entry;
    } else {
        fprintf(stderr, "Coudn't find parent id\n");
        exit(-1);
    }
    return envp;
}

void update_environ(char **envp) {
    if (!envp)
        return;

    int i = find_key_index(envp, CLADE_PARENT_ID_ENV);

    // i can be -1 when Clade environment variables can be found in environ,
    // but were deleted from envp by some other process
    if (i != -1) {
        setenv(CLADE_PARENT_ID_ENV, strchr(envp[i], '=') + 1, 1);
    }
}

static int get_cmd_id_and_update() {
    int id = get_cmd_id();

    id++;

    char *id_file = getenv(CLADE_ID_FILE_ENV);
    FILE *f = fopen(id_file, "w");
    if (!f) {
        fprintf(stderr, "Couldn't open %s file for write\n", id_file);
        exit(EXIT_FAILURE);
    }

    int ret = fprintf(f, "%d", id);
    if (ret <= 0) {
        fprintf(stderr, "Couldn't write data to file %s\n", id_file);
        exit(EXIT_FAILURE);
    }

    fclose(f);

    return id;
}

int get_cmd_id() {
    char *id_file = getenv(CLADE_ID_FILE_ENV);

    FILE *f = fopen(id_file, "r");
    if (!f) {
        fprintf(stderr, "Couldn't open %s file for read\n", id_file);
        exit(EXIT_FAILURE);
    }

    int id;
    int ret = fscanf(f, "%d", &id);
    if (ret <= 0) {
        fprintf(stderr, "Couldn't read data from file %s\n", id_file);
        exit(EXIT_FAILURE);
    }

    fclose(f);

    return id;
}

char *get_parent_id() {
    char *parent_id = strdup(getenv(CLADE_PARENT_ID_ENV));

    int new_parent_id = get_cmd_id_and_update();
    char new_clade_id[50]; // 50 should be enough

    sprintf(new_clade_id, "%d", new_parent_id);
    setenv(CLADE_PARENT_ID_ENV, new_clade_id, 1);

    return parent_id;
}

extern char *getenv_or_fail(const char *name) {
    char *value = getenv(name);

    if (!value) {
        fprintf(stderr, "Environment is not prepared: %s is not specified\n", name);
        exit(EXIT_FAILURE);
    }

    return value;
}
