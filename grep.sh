EXCLUDE="--exclude=*.vcxproj.filters"

find $1 -iname "*.s"
grep -R "asm" $1 ${EXCLUDE}
