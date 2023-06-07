# TX SX Pro Custom Payload Packer - by CTCaer 
# Edited by mleb :p

import struct, hashlib, sys
from os import unlink

def sha256(data):
	sha256 = hashlib.new('sha256')
	sha256.update(data)
	return sha256.digest()

boot_fn = 'boot.dat'
stage2_fn = sys.argv[1]

boot = open(boot_fn, 'wb')

with open(stage2_fn, 'rb') as fh:
	stage2 = bytearray(fh.read())
	stage2 = bytes(stage2)

header = b''

header += b'\x43\x54\x43\x61\x65\x72\x20\x42\x4F\x4F\x54\x00'

header += b'\x56\x32\x2E\x35'

header += sha256(stage2)

header += b'\x00\x00\x01\x40'

header += struct.pack('I', len(stage2))

header += struct.pack('I', 0)

header += b'\x00' * 0xA4

sha256 = hashlib.new('sha256')

sha256.update(header)

header += sha256.digest()

boot.write(header)

boot.write(stage2)

boot.close()
