#!/usr/bin/env bash
# fetch_third_party.sh: clone the third-party sources at the commits pinned in docs/TOOLS.md.
# Inputs: none. Output: third_party/<name>/ checked out at the pinned commit.
# Usage: scripts/fetch_third_party.sh   (run from the writehammer/ directory)
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p third_party

fetch() { # name url commit
    local name=$1 url=$2 commit=$3
    if [ ! -d "third_party/$name/.git" ]; then
        git init -q "third_party/$name"
        git -C "third_party/$name" remote add origin "$url"
    fi
    git -C "third_party/$name" fetch -q --depth 1 origin "$commit"
    git -C "third_party/$name" checkout -q --detach "$commit"
    echo "$name $(git -C "third_party/$name" rev-parse HEAD)"
}

fetch riscv-arch-test https://github.com/riscv-non-isa/riscv-arch-test.git fc32e41d49480fd99ba0a192dfff9c3319b44873
fetch coremark        https://github.com/eembc/coremark.git                1f483d5b8316753a742cbf5590caf5bd0a4e4777
fetch embench-iot     https://github.com/embench/embench-iot.git           09c2ed8c3b7008c95d08b038de4a3f6dc103ed70
fetch riscv-tests     https://github.com/riscv-software-src/riscv-tests.git 3df703cd52d5f0d8224e3c50bf03c6cb70efff98
