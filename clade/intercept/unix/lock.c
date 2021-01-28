#include <sys/file.h>
#include <stdio.h>
#include <stdlib.h>

#include "env.h"

static FILE *f;

void clade_lock(void) {
    char *id_file = getenv_or_fail(CLADE_ID_FILE_ENV);

    f = fopen(id_file, "r");
    if (!f) {
        fprintf(stderr, "Couldn't open %s file\n", id_file);
        exit(EXIT_FAILURE);
    }

    flock(fileno(f), LOCK_EX);
}

void clade_unlock(void) {
    fclose(f);
    flock(fileno(f), LOCK_UN);
}
