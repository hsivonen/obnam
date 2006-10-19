import os

import wibbrlib

def encode1(i):
    if i == 0:
        return chr(0)
    else:
        septets = []
        while i > 0:
            octet = i & 0x7f
            if septets:
                octet = octet | 0x80
            septets.insert(0, chr(octet))
            i = i >> 7
        return "".join(septets)

def decode1(str, pos):
    value = 0
    len_str = len(str)
    while pos < len_str:
        octet = ord(str[pos])
        pos += 1
        if octet < 2**7:
            value = (value << 7) | octet
            break
        else:
            value = (value << 7) | (octet & 0x7f)
    return value, pos

def encode2(i):
    s = "%d" % i
    return chr(len(s)) + s

def decode2(encoded, pos):
    n = ord(encoded[pos])
    return int(encoded[pos+1:pos+1+n]), pos+1+n

def encode3(i):
    return "%d\n" % i

def decode3(encoded, pos):
    i = encoded.find("\n", pos)
    if i == -1:
        return -1, pos
    else:
        return int(encoded[pos:i]), i+1

def measure(enc, dec, n):
    assert dec(enc(12765), 0)[0] == 12765

    times1 = os.times()
    for i in range(n):
        enc(12765)
    times2 = os.times()
    t1 = times2[0] - times1[0]
    
    encoded = enc(12765)
    times1 = os.times()
    for i in range(n):
        dec(encoded, 0)
    times2 = os.times()
    t2 = times2[0] - times1[0]
    
    return t1, t2

N = 1000 * 1000

funcs = (("bit twiddling", encode1, decode1), 
         ("length byte", encode2, decode2),
         ("netint", encode3, decode3))

for desc, enc, dec in funcs:
    (t1, t2) = measure(enc, dec, N)
    print desc, t1, t2
