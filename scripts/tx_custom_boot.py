# TX SX Pro Custom Payload Packer - by CTCaer, edited by mleb :p

import struct, hashlib, sys

def sha256(data):
    sha256 = hashlib.sha256()
    sha256.update(data)
    return sha256.digest()

def pack_payload(file_path, output_file):
    with open(file_path, "rb") as fh:
        stage2 = bytearray(fh.read())

    header = b"CTCaer BOOT\x00"
    header += b"V2.5"

    stage2_hash = sha256(stage2)
    header += stage2_hash

    header += b"\x00\x00\x01\x40"

    header += struct.pack("I", len(stage2))
    header += struct.pack("I", 0)

    header += b"\x00" * 0xA4

    header_hash = hashlib.sha256()
    header_hash.update(header)
    header += header_hash.digest()

    with open(output_file, "wb") as boot:
        boot.write(header)
        boot.write(stage2)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python tx_custom_boot.py <input_file> <output_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    pack_payload(input_file, output_file)