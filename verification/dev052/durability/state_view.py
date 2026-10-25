"""Read-only fixture inspector for bbolt v2 pages; never writes checkpoint state.

Snapshots must be taken with the collector SIGSTOPped or stopped. This is not a
repair/conversion tool. Validate meta FNV checksums and page bounds before reads.
"""

import hashlib
import json
from pathlib import Path
import re
import struct


def fnv(data):
    value = 14695981039346656037
    for byte in data:
        value = ((value ^ byte) * 1099511628211) & ((1 << 64) - 1)
    return value


def records(data):
    size = struct.unpack_from("<I", data, 24)[0]
    if size < 1024 or size > 65536:
        raise ValueError("Unsupported bbolt page size")
    metas = []
    for page in [0, 1]:
        offset = page * size + 16
        meta = data[offset : offset + 64]
        magic, version = struct.unpack_from("<II", meta)
        if (
            magic == 0xED0CDAED
            and version == 2
            and fnv(meta[:56]) == struct.unpack_from("<Q", meta, 56)[0]
        ):
            metas.append(
                (
                    struct.unpack_from("<Q", meta, 48)[0],
                    struct.unpack_from("<Q", meta, 16)[0],
                )
            )
    if not metas:
        raise ValueError("No valid committed bbolt metadata page")
    txid, root = max(metas)
    output = []

    def walk(page_data, prefix, depth=0):
        if depth > 32 or len(page_data) < 16:
            raise ValueError("Invalid bbolt tree")
        _, flags, count, _ = struct.unpack_from("<QHHI", page_data)
        for index in range(count):
            element = 16 + index * 16
            if flags & 1:  # branch page
                _, _, child = struct.unpack_from("<IIQ", page_data, element)
                walk(data[child * size :], prefix, depth + 1)
                continue
            if not flags & 2:
                raise ValueError("Unexpected bbolt page flags")
            kind, position, key_size, value_size = struct.unpack_from(
                "<IIII", page_data, element
            )
            start = element + position
            key = page_data[start : start + key_size]
            value = page_data[start + key_size : start + key_size + value_size]
            if len(value) != value_size:
                raise ValueError("Truncated bbolt element")
            path = prefix + [key.decode(errors="backslashreplace")]
            if kind & 1:
                child = struct.unpack_from("<Q", value)[0]
                walk(
                    value[16:] if child == 0 else data[child * size :], path, depth + 1
                )
            else:
                output.append((path, value))

    walk(data[root * size :], [])
    return txid, output


def varints(data):
    result = {}
    position = 0

    def integer():
        nonlocal position
        value = shift = 0
        while position < len(data) and shift <= 63:
            byte = data[position]
            position += 1
            value |= (byte & 127) << shift
            if byte < 128:
                return value
            shift += 7
        raise ValueError("Bad varint")

    while position < len(data):
        tag = integer()
        field, wire = tag >> 3, tag & 7
        if wire == 0:
            value = integer()
        elif wire == 2:
            length = integer()
            value = data[position : position + length]
            position += length
        elif wire in [1, 5]:
            length = 8 if wire == 1 else 4
            value = data[position : position + length]
            position += length
        else:
            raise ValueError("Unsupported wire field")
        result.setdefault(field, []).append(value)
    return result


def inspect(root):
    result = {}
    for file in sorted(Path(root).glob("*")):
        if not file.is_file():
            continue
        data = file.read_bytes()
        txid, entries = records(data)
        rows = []
        for path, value in entries:
            row = {
                "key": path,
                "bytes": len(value),
                "sha256": hashlib.sha256(value).hexdigest(),
                "event_ids": sorted(
                    set(x.decode() for x in re.findall(rb"event-[0-9]{4}", value))
                ),
            }
            try:
                row["json"] = json.loads(value)
            except (ValueError, UnicodeDecodeError):
                if file.name.startswith("receiver_filelog"):
                    try:
                        lines = value.decode().splitlines()
                        if lines and lines[0].isdigit():
                            row["legacy_checkpoint_records"] = [
                                json.loads(line) for line in lines[1:]
                            ]
                    except (ValueError, UnicodeDecodeError):
                        pass
                # Native .163 MetadataList => Metadata offset(2), record_num(3).
                if file.name.startswith("receiver_filelog"):
                    try:
                        fields = varints(value)
                        hints = []
                        for item in fields.get(1, []):
                            if isinstance(item, bytes):
                                metadata = varints(item)
                                if 2 in metadata:
                                    hints.append(
                                        {
                                            "offset": metadata[2][0],
                                            "record_num": metadata.get(3, [None])[0],
                                        }
                                    )
                        if hints:
                            row["protobuf_checkpoint_offsets"] = hints
                    except (ValueError, IndexError, TypeError):
                        pass
            if path[-1] == "qmv0":
                fields = varints(value)

                def fixed(number):
                    return struct.unpack("<Q", fields.get(number, [b"\x00" * 8])[0])[0]

                dispatched = []
                for packed in fields.get(5, []):
                    dispatched.extend(
                        struct.unpack("<" + "Q" * (len(packed) // 8), packed)
                    )
                row["queue_metadata"] = {
                    "read_index": fixed(3),
                    "write_index": fixed(4),
                    "dispatched": dispatched,
                }
            rows.append(row)
        result[file.name] = {
            "file_sha256": hashlib.sha256(data).hexdigest(),
            "committed_txid": txid,
            "entries": rows,
        }
    return result
