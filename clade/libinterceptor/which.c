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

// Lookup executable `name` within the PATH environment variable
char *which(const char *name) {
  return which_path(name, getenv("PATH"));
}

// Lookup executable `name` within `path`
char *which_path(const char *name, const char *_path) {
  char *path = strdup(_path);

  if (!path)
    return NULL;

  char *tok = strtok(path, WHICH_DELIMITER);

  while (tok) {
    // path
    int len = strlen(tok) + 2 + strlen(name);
    char *file = malloc(len);

    if (!file) {
      free(path);
      return NULL;
    }

    sprintf(file, "%s/%s", tok, name);

    // executable
    if (!access(file, X_OK)) {
      free(path);
      return file;
    }

    // next token
    tok = strtok(NULL, WHICH_DELIMITER);
    free(file);
  }

  free(path);

  return NULL;
}
