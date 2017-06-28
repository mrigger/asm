EXCLUDE="--exclude=*.vcxproj.filters --exclude=*.html --exclude=*.js --exclude=*.md"

find $1 -iname "*.s"
grep -R "asm" $1 ${EXCLUDE}
