"""Read-only ELF/Go metadata inspection. Never loads or executes the binary."""

import hashlib
import json
from pathlib import Path
import struct
import sys

EXPECTED = "52c8749d0142edd234e9d6bd5237dff2d81e71f43537e2f4f66f75dd4b243dd0"


def inspect(path):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != EXPECTED:
        raise ValueError("Not the reviewed gosu bytes")
    if data[:6] != b"\x7fELF\x02\x01":
        raise ValueError("Only reviewed ELF64 little-endian is qualified")
    shoff = struct.unpack_from("<Q", data, 40)[0]
    entsize, count, string_index = struct.unpack_from("<HHH", data, 58)
    headers = [
        struct.unpack_from("<IIQQQQIIQQ", data, shoff + i * entsize)
        for i in range(count)
    ]
    string_header = headers[string_index]
    names = data[string_header[4] : string_header[4] + string_header[5]]
    sections = {
        names[h[0] :].split(b"\0", 1)[0].decode(): data[h[4] : h[4] + h[5]]
        for h in headers
    }
    build = sections[".go.buildinfo"]
    assert build[:14] == b"\xff Go buildinf:" and build[15] & 2

    def string(b):
        n = 0
        shift = 0
        for index, c in enumerate(b):
            n |= (c & 127) << shift
            if c < 128:
                return b[index + 1 : index + 1 + n], b[index + 1 + n :]
            shift += 7
        raise ValueError("Invalid Go inline string")

    version, rest = string(build[32:])
    module, _ = string(rest)
    module = module[16:-16].decode()
    pcln = sections[".gopclntab"]
    magic = struct.unpack_from("<I", pcln)[0]
    if magic != 0xFFFFFFF1 or pcln[7] != 8:
        raise ValueError("Unqualified pclntab format")
    nfunc = struct.unpack_from("<Q", pcln, 8)[0]
    nameoff = struct.unpack_from("<Q", pcln, 32)[0]
    tableoff = struct.unpack_from("<Q", pcln, 64)[0]
    if nfunc > 100000:
        raise ValueError("Unexpected function count")
    functions = []
    for index in range(nfunc):
        offset = struct.unpack_from("<I", pcln, tableoff + index * 8 + 4)[0]
        name = struct.unpack_from("<i", pcln, tableoff + offset + 4)[0]
        if name < 0:
            raise ValueError("Invalid function offset")
        functions.append(pcln[nameoff + name :].split(b"\0", 1)[0].decode())
    return {
        "sha256": EXPECTED,
        "go_version": version.decode(),
        "module_build_info": module,
        "elf_sections": sorted(sections),
        "pclntab_magic": hex(magic),
        "pclntab_function_count": len(functions),
        "function_names": functions,
        "limitations": [
            "Names are observed from Go pclntab, not a complete call graph",
            "Inlining, indirect calls and compiler/runtime internals prevent an absence proof",
            "No runtime execution or database/image operation performed",
        ],
    }


if __name__ == "__main__":
    result = inspect(Path(sys.argv[1]))
    Path(sys.argv[2]).write_text(json.dumps(result, indent=2) + "\n")
    print(
        "Reviewed binary hash and static Go metadata:",
        result["go_version"],
        result["pclntab_function_count"],
        "function names; not exploitability certification",
    )
