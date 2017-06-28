int main() {
    char data[20];
    __asm__ __volatile__ ("" : : "r" (data) : "memory");
}
