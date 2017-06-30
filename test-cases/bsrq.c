#include <stdint.h>
#include <assert.h>

int main() {
  /* A value of zero is undefined */
  int64_t msb, val;
  val = 1;
  asm("bsrq %1,%0" : "=r"(msb) : "r"(val));
  assert(msb == 0);
  val = 2;
  asm("bsrq %1,%0" : "=r"(msb) : "r"(val));
  assert(msb == 1);
  val = -1;
  asm("bsrq %1,%0" : "=r"(msb) : "r"(val));
  assert(msb == 63);
  val = 123;
  asm("bsrq %1,%0" : "=r"(msb) : "r"(val));
  assert(msb == 6);
  val = 23123123123L;
  asm("bsrq %1,%0" : "=r"(msb) : "r"(val));
  assert(msb == 34);
}
