#include <stdio.h>
#include "zero.h"

static void print(char *msg) {
    printf("%s\n", msg);
}

int main() {
    print("Hello");
    return zero();
}
