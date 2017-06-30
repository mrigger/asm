#include <stdint.h>
#include <assert.h>

int main() {
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
