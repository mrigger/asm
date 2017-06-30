#include <stdint.h>
#include <assert.h>

int main() {
    /* A value of zero is undefined */
    int32_t val1 = 1;
    int32_t val2 = 3;
    int32_t val3 = -1;
    int32_t val4 = 1234;
    int32_t msb;
    asm("bsrl %1,%0" : "=r"(msb) : "r"(val1));
    assert(msb == 0);
    asm("bsrl %1,%0" : "=r"(msb) : "r"(val2));
    assert(msb == 1);
    asm("bsrl %1,%0" : "=r"(msb) : "r"(val3));
    assert(msb == 31);
    asm("bsrl %1,%0" : "=r"(msb) : "r"(val4));
    assert(msb == 10);
}
