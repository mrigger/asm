#include <stdint.h>
#include <assert.h>

void crc32b() {
    uint32_t crc;
    uint8_t value;
    crc = 0;
    value = 120;
    asm("crc32b %[value], %[crc]\n" : [crc] "+r" (crc) : [value] "rm" (value));
    assert(crc == -79622974);
    crc = 1;
    value = -1;
    asm("crc32b %[value], %[crc]\n" : [crc] "+r" (crc) : [value] "rm" (value));
    assert(crc == 1595330642);
    crc = 21;
    value = -33;
    asm("crc32b %[value], %[crc]\n" : [crc] "+r" (crc) : [value] "rm" (value));
    assert(crc == -1469116676);
    crc = 0;
    value = 0;
    asm("crc32b %[value], %[crc]\n" : [crc] "+r" (crc) : [value] "rm" (value));
    assert(crc == 0);
}

void crc32l() {
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

void crc32q() {
    uint64_t crc, value;
    crc = 0;
    value = 34234123123L;
    asm("crc32q %[value], %[crc]\n" : [crc] "+r" (crc) : [value] "rm" (value));
    assert(crc == 3005937269);
    crc = 1;
    value = -1;
    asm("crc32q %[value], %[crc]\n" : [crc] "+r" (crc) : [value] "rm" (value));
    assert(crc == 2373157994);
    crc = 21;
    value = 4534512343452;
    asm("crc32q %[value], %[crc]\n" : [crc] "+r" (crc) : [value] "rm" (value));
    assert(crc == 1462127879);
    crc = 0;
    value = 0;
    asm("crc32q %[value], %[crc]\n" : [crc] "+r" (crc) : [value] "rm" (value));
    assert(crc == 0);
}

void crc32w() {
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

int main() {
    crc32b();
    crc32l();
    crc32q();
    crc32w();
}
