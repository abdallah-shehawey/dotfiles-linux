#!/bin/bash
# Stop the private shell and its fixture clients.
cd "$(dirname "$0")"
touch stop
for i in $(seq 1 40); do [ -f env.sh ] || break; sleep 0.5; done
pkill -f '^python3 .*fixture\.py' 2>/dev/null
rm -f stop
echo stopped
