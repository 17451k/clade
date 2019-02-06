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

static char *key = "CLADE_PARENT_ID";

static int get_envp_len(char **envp) {
    int i;
    for(i = 0; envp[i] != NULL; i++);
    return i;
}

static char **copy_envp(char **envp) {
    int envp_len = get_envp_len(envp);
    char **copy = malloc((envp_len + 1) * sizeof(char *));

    int i;
    for (i = 0; i < envp_len; i++) {
        copy[i] = strdup(envp[i]);
    }

    copy[i] = 0;
    return copy;
}

static int find_parent_id(char **envp) {
    int key_len = strlen(key);
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

    exit(-1);

}

char **update_envp(char **input_envp) {
    if (!input_envp)
        return input_envp;

    char *value = getenv(key);
    size_t new_value_len = strlen(key) + strlen(value) + 2;
    char *new_value = malloc(new_value_len);
    snprintf(new_value, new_value_len, "%s=%s", key, value);

    char **envp = copy_envp(input_envp);
    int i = find_parent_id(envp);
    free(envp[i]);
    envp[i] = new_value;
    return envp;
}

void update_environ(char **envp) {
    if (!envp)
        return;

    int i = find_parent_id(envp);
    setenv(key, strchr(envp[i], '=') + 1, 1);
}

static int get_cmd_id() {
    char *id_file = getenv("CLADE_ID_FILE");

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

    id++;

    f = fopen(id_file, "w");
    if (!f) {
        fprintf(stderr, "Couldn't open %s file for write\n", id_file);
        exit(EXIT_FAILURE);
    }

    ret = fprintf(f, "%d", id);
    if (ret <= 0) {
        fprintf(stderr, "Couldn't write data to file %s\n", id_file);
        exit(EXIT_FAILURE);
    }

    fclose(f);

    return id;
}

char *get_parent_id() {
    char *parent_id = strdup(getenv(key));

    int new_parent_id = get_cmd_id();
    char new_clade_id[50]; // 50 should be enough

    sprintf(new_clade_id, "%d", new_parent_id);
    setenv(key, new_clade_id, 1);

    return parent_id;
}
