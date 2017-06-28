#include <inttypes.h>

int main() {
    uint32_t val;
    uint32_t* ptr = &val;
    uint64_t rax,rdx;
    asm volatile ( "rdtscp\n" : "=a" (rax), "=d" (rdx), "=c" (ptr) : : "%rcx", "%rdx" );
}
