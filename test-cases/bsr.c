#include <stdint.h>
#include <assert.h>

void bsrq() {
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

void bsrl() {
  /* A value of zero is undefined */
  int32_t val1 = 1;
  int32_t val2 = 3;
  int32_t val3 = -1;
  int32_t val4 = 1234;
  int32_t msb;
  asm("bsrl %1,%0" : "=r"(msb) : "r"(val1));
  assert(msb == 0);
  asm("bsrl %1,%0" : "=r"(msb) : "r"(val2));
  assert(msb == 1);
  asm("bsrl %1,%0" : "=r"(msb) : "r"(val3));
  assert(msb == 31);
  asm("bsrl %1,%0" : "=r"(msb) : "r"(val4));
  assert(msb == 10);
}

int main() {
  bsrq();
  bsrl();
}

SELECT AsmInstruction.ID, AsmInstruction.INSTRUCTION, SUM(AsmSequencesInGithubProject.NR_OCCURRENCES) total_count FROM AsmSequenceInstruction, AsmInstruction, AsmSequencesInGithubProject WHERE AsmInstruction.ID = AsmSequenceInstruction.ASM_INSTRUCTION_ID AND AsmSequencesInGithubProject.ASM_SEQUENCE_ID = AsmSequenceInstruction.ASM_SEQUENCE_ID GROUP BY AsmInstruction.INSTRUCTION, AsmInstruction.ID ORDER BY total_count DESC
