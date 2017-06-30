#include <stdint.h>
#include <assert.h>

int main() {
    int8_t result = -1;
    __asm __volatile("sete %0" : "=r" (result) :  :);
    assert(result == 0 || result == 1);
}
