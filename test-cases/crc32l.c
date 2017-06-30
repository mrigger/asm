#include <stdint.h>
#include <assert.h>

int main() {
    uint32_t crc, value;
    crc = 0;
    value = 34234123;
    asm("crc32l %[value], %[crc]\n" : [crc] "+r" (crc) : [value] "rm" (value));
    assert(crc == 879414913);
    crc = 1;
    value = -1;
    asm("crc32l %[value], %[crc]\n" : [crc] "+r" (crc) : [value] "rm" (value));
    assert(crc == 1792876160);
    crc = 21;
    value = 453451252;
    asm("crc32l %[value], %[crc]\n" : [crc] "+r" (crc) : [value] "rm" (value));
    assert(crc == 1940977873);
    crc = 0;
    value = 0;
    asm("crc32l %[value], %[crc]\n" : [crc] "+r" (crc) : [value] "rm" (value));
    assert(crc == 0);
}
