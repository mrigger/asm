int main() {
    int result, x;
    __asm__("bswap %0" : "=r" (result) : "0" (x));
    __asm__ ("bswap %0" : "=r" (result) : "0" (x)); // space after __
    __asm__     ("bswap %0" : "=r" (result) : "0" (x)); // several spaces after __
    __asm__    
            ("bswap %0" : "=r" (result) : "0" (x)); // instruction in the next line
    __asm__    
            ("bswap %0" : "=r" (result) : "0" (x)); // instruction in the next line
    __asm__ 		("bswap %0" : "=r" (result) : "0" (x)); // two tabs
    __asm("bswap %0" : "=r" (result) : "0" (x));
    __asm   ("bswap %0" : "=r" (result) : "0" (x));
    asm   ("bswap %0" : "=r" (result) : "0" (x));
}
