grep -E -R "(__)?asm(__)?" $1
find $1 -iname "*.s"
grep -R "asm" $1
