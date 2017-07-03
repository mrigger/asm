#include <stdint.h>

void testI8() {
    uint32_t val = 5;
    uint32_t update = 123;
    uint32_t expected = 5;
    uint32_t* mem = &val;
    __asm __volatile ("lock cmpxchgl %2, %0;" : "+m" (mem), "+a" (expected) : "r" (update) : "memory", "cc" );
    printf("%d %d\n", val, *mem);
}

int main() {
    testI8();
}
