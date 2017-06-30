#include <stdint.h>

int main() {
   uint32_t ctr = 5;
   uint32_t a, d;
   __asm("xgetbv" : "=a"(a),"=d"(d) : "c"(1) : );
   uint64_t result = a | ((uint64_t) d << 32);
   printf("%ld\n", result);
}
