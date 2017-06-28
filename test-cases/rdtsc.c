#include <assert.h>

int main() {
    long first, second;
    __asm__ __volatile__("rdtsc" : "=A"(first) : :);
    do {
        __asm__ __volatile__("rdtsc" : "=A"(second) : :);
    } while (first == second);
    assert(second > first);
}
