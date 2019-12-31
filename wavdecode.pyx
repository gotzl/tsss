# cython: nonecheck=True
#        ^^^ Turns on nonecheck globally

def decode(bytes, fac):
    import struct
    data = []
    for i in range(0, len(bytes), 3):
        b = bytes[i:i+3]
        b = bytearray([0]) + b
        data.append(struct.unpack('i',b)[0]>>8)
    return data

def encode(data):
    bytes = bytearray()
    for i in data:
        bytes += bytearray([(i>>24)&0xff, (i>>16)&0xff, (i>>8)&0xff])
    return bytes