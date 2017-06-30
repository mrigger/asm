#include <stdint.h>
#include <assert.h>

int main() {
    uint32_t crc;
    uint16_t value;
    crc = 0;
    value = 34223;
    asm("crc32w %[value], %[crc]\n" : [crc] "+r" (crc) : [value] "rm" (value));
    assert(crc == -734643102);
    crc = 1;
    value = -1;
    asm("crc32w %[value], %[crc]\n" : [crc] "+r" (crc) : [value] "rm" (value));
    assert(crc == 490532773);
    crc = 21;
    value = -32423;
    asm("crc32w %[value], %[crc]\n" : [crc] "+r" (crc) : [value] "rm" (value));
    assert(crc == 1544870939);
    crc = 0;
    value = 0;
    asm("crc32w %[value], %[crc]\n" : [crc] "+r" (crc) : [value] "rm" (value));
    assert(crc == 0);
}
