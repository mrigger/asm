EXCLUDE="--exclude=*.vcxproj.filters"

grep -E -R "(__)?asm(__)?" $1 ${EXCLUDE}
find $1 -iname "*.s"
grep -R "asm" $1 ${EXCLUDE}
