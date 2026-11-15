#!/bin/bash
# Rebuild libSDL2-2.0.so.0 here (needed after an SDL2 update changes its file name).
set -e
cd "$(dirname "$(readlink -f "$0")")"
REAL=$(readlink -f /usr/lib64/libSDL2-2.0.so.0)
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
# a stub whose soname is the real library's full path, so the boost library
# loads the real one by path instead of finding itself by name
echo 'void rumble_boost_stub(void){}' > "$T/stub.c"
gcc -shared -fPIC -o "$T/libstub.so" "$T/stub.c" -Wl,-soname,"$REAL"
gcc -O2 -shared -fPIC -Wall -DREAL_SDL2="\"$REAL\"" -o libSDL2-2.0.so.0 rumble-boost.c \
    -Wl,-soname,libSDL2-2.0.so.0 -Wl,--no-as-needed "$T/libstub.so" -ldl -lpthread
echo "built against $REAL"
