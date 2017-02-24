import math
import os
import struct
import sys

import cairo
from colorsys import hsv_to_rgb

def data_to_pic(name, w, h, data, cols):
    SIZE = 8
    WIDTH, HEIGHT = SIZE * w + 1, SIZE * h + 1

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH, HEIGHT)
    ctx = cairo.Context(surface)

    ctx.set_source_rgb(0, 0, 0)
    ctx.rectangle(0, 0, WIDTH, HEIGHT)
    ctx.fill()

    for y in range(h):
        for x in range(w):
            ctx.set_source_rgb(*cols[int(bool(data[y] & (1 << x)))])
            ctx.rectangle(1 + x * SIZE, 1 + y * SIZE, SIZE - 1, SIZE - 1)
            ctx.fill()

    surface.write_to_png(name + '.png')

def read_from_pdf(name):
    # return an array of 512-bit message blocks (each grouped in 32-bit words)

    with open(name + '.pdf', 'rb') as f:
        data = f.read()

    # pad
    n = len(data)
    data += chr(0x80)
    data += chr(0x00) * ((56 - len(data)) % 64)
    data += struct.pack('>Q', n)
    assert len(data) % 64 == 0, len(data)

    # split into message blocks of 16 words == 64 bytes
    return [struct.unpack('>IIIIIIIIIIIIIIII', data[i:i + 64]) for i in range(0, len(data), 64)]

u32_max = (1 << 32) - 1

def rotl(x, n):
    return ((x << n) & u32_max) | (x >> (32 - n))

def sha1_block(h_in, block):
    w = list(block)
    for i in range(16, 80):
        w.append(rotl(w[i - 3] ^ w[i - 8] ^ w[i - 14] ^ w[i - 16], 1))

    state = [
        rotl(h_in[4], 2),
        rotl(h_in[3], 2),
        rotl(h_in[2], 2),
        rotl(h_in[1], 0),
        rotl(h_in[0], 0),
    ]

    for i in range(80):
        a = rotl(state[i + 4], 5)
        b = state[i + 3]
        c = rotl(state[i + 2], 30)
        d = rotl(state[i + 1], 30)
        e = rotl(state[i + 0], 30)

        if i >= 0 and i < 20:
            f = (b & c) | (~b & d)
            k = 0x5A827999
        elif i >= 20 and i < 40:
            f = b ^ c ^ d
            k = 0x6ED9EBA1
        elif i >= 40 and i < 60:
            f = (b & c) | (b & d) | (c & d)
            k = 0x8F1BBCDC
        elif i >= 60 and i < 80:
            f = b ^ c ^ d
            k = 0xCA62C1D6

        state.append((a + f + e + k + w[i]) & u32_max)

    h_out = [
        (h_in[0] + state[84]) & u32_max,
        (h_in[1] + state[83]) & u32_max,
        (h_in[2] + rotl(state[82], 30)) & u32_max,
        (h_in[3] + rotl(state[81], 30)) & u32_max,
        (h_in[4] + rotl(state[80], 30)) & u32_max,
    ]

    return w, state, h_out

def sha1(blocks):
    result = []

    h = [0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0]
    for block in blocks:
        w, state, h = sha1_block(h, block)
        result.append((w, state, h))

    return result

good = sha1(read_from_pdf('good'))
bad = sha1(read_from_pdf('bad'))

delta = [[[x2 ^ y2 for x2, y2 in zip(x1, y1)] for x1, y1 in zip(x0, y0)] for x0, y0 in zip(good, bad)]

sat = .7

grey = (
    hsv_to_rgb(0. / 6, 0, .25),
    hsv_to_rgb(0. / 6, 0, .75),
)

red = (
    hsv_to_rgb(0. / 6, sat, .5),
    hsv_to_rgb(0. / 6, sat, 1),
)

yellow = (
    hsv_to_rgb(1. / 6, sat, .5),
    hsv_to_rgb(1. / 6, sat, 1),
)

green = (
    hsv_to_rgb(2. / 6, sat, .5),
    hsv_to_rgb(2. / 6, sat, 1),
)

def output(name, data):
    for block in data:
        data_to_pic(name + '-m0',   32, 16, data[3][0][  :16], grey)
        data_to_pic(name + '-m0_w', 32, 64, data[3][0][16:  ], red)
        data_to_pic(name + '-m0_a', 32, 85, data[3][1][  :  ], yellow)
        data_to_pic(name + '-m0_h', 32,  5, data[3][2],        green)

        data_to_pic(name + '-m1',   32, 16, data[4][0][  :16], grey)
        data_to_pic(name + '-m1_w', 32, 64, data[4][0][16:  ], red)
        data_to_pic(name + '-m1_a', 32, 85, data[4][1][  :  ], yellow)
        data_to_pic(name + '-m1_h', 32,  5, data[4][2],        green)

output('good', good)
output('bad', bad)
output('xor', delta)
