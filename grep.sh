EXCLUDE="--exclude=*.vcxproj.filters --exclude=*.html --exclude=*.js --exclude=*.md --exclude=*.png --exclude=*.base64"

find $1 -iname "*.s"
grep -R "asm" $1 ${EXCLUDE}
