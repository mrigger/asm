#include <stdint.h>
#include <assert.h>

int main() {
  /* A value of zero is undefined */
  int64_t msb, val;
  val = 1;
  asm("bsfq %1,%0" : "=r"(msb) : "r"(val));
  assert(msb == 0);
  val = 2;
  asm("bsfq %1,%0" : "=r"(msb) : "r"(val));
  assert(msb == 1);
  val = -1;
  asm("bsfq %1,%0" : "=r"(msb) : "r"(val));
  assert(msb == 0);
  val = 2L << 53;
  asm("bsfq %1,%0" : "=r"(msb) : "r"(val));
  assert(msb == 54);
  val = 2L << 52 | 2L << 51 | 2L << 50;
  asm("bsfq %1,%0" : "=r"(msb) : "r"(val));
  assert(msb == 51);
}
