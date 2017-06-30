int main() {
    asm volatile("mfence" ::: "memory");
}
