[![Build Status](https://travis-ci.org/mrigger/asm.svg?branch=master)](https://travis-ci.org/mrigger/asm)


Downloading a project:

```
./asm.py database.db download-project --file=https://github.com/mattsta/crcspeed
./asm.py database.db download-project --file=https://github.com/mattsta/crcspeed --keywords=crc
```

Associating an inline assembly instruction sequence with a file in a project:

```
./asm.py database.db add-project-asm-sequence --instr="rdtsc" --file="projects/mattsta-crcspeed/main.c"
```

Add an assembly instruction (or update a test case):

```
./asm.py database.db add-asm-instruction --instr="rdtsc" --file="test.c"
```

Add keywords to a project:

```
./asm.py database.db add-project-keywords --file=https://github.com/mattsta/crcspeed --keywords=crc
```

Display the keywords in a tree:

```
./asm.py database.db categories
```
