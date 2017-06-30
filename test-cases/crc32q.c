#include <stdint.h>
#include <assert.h>

int main() {
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
