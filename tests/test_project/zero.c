#include <stdio.h>

#define WEIRD_ZERO(X) X - X
#define ZERO WEIRD_ZERO(10)

int zero() {
    return ZERO;
}

static void print(char *msg) {
    printf("%s\n", msg);
}

int func_with_pointers() {
    int (*fp1)(void) = zero;
    int (*fp2)(void) = zero;
    return fp1() + fp2();
}

typedef unsigned char super_char;

int (*fp3[])(void) = {zero};
