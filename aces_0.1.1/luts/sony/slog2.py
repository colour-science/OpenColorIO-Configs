#!/usr/bin/env python

import math

# IT's annoying that the 1023,4 and 4095,16 almost, but dont exactly, cancel. UGH
# The intent is clearly to have the same mapping, but it's not done very well.
# Sony engineers and/or the Academy should pick one of these mappings for both.

def SLog_to_lin(x):
    return (math.pow(10.0,(((((x*1023.0)/4.0-16.0)/219.0)-0.616596-0.03)/0.432699))-0.037584)*0.9

def Fit(value, fromMin, fromMax, toMin, toMax):
    if fromMin == fromMax:
        raise ValueError("fromMin == fromMax")
    return (value - fromMin) / (fromMax - fromMin) * (toMax - toMin) + toMin

def SLog2_to_lin(x):
    x = Fit(x, 64.0/1023.0, 940.0/1023.0, 0.0, 1.0)
    if x < 0.030001222851889303:
        y = ((x-0.030001222851889303 ) * 0.28258064516129)
    else:
        y = (219.0*(math.pow(10.0, ((x-0.616596-0.03)/0.432699)) - 0.037584) /155.0)
    return y*0.9
    
"""
steps = 1024
for i in xrange(steps):
    x = i/(steps-1.0)
    print x, SLog2_to_lin(x)
"""
"""
print SLog2_to_lin_copy(90.0/1023.0) / 0.9
print SLog2_to_lin_copy(91.0/1023.0) / 0.9
print SLog2_to_lin_copy(582.0/1023.0) / 0.9
print SLog2_to_lin_copy(940.0/1023.0) / 0.9
print SLog2_to_lin_copy(998.0/1023.0) / 0.9
"""

def WriteSPI1D(filename, fromMin, fromMax, data):
    f = file(filename,'w')
    f.write("Version 1\n")
    f.write("From %s %s\n" % (fromMin, fromMax))
    f.write("Length %d\n" % len(data))
    f.write("Components 1\n")
    f.write("{\n")
    for value in data:
        f.write("        %s\n" % value)
    f.write("}\n")
    f.close()

NUM_SAMPLES = 2**14
RANGE = (-0.125, 1.125)
data = []
for i in xrange(NUM_SAMPLES):
    x = i/(NUM_SAMPLES-1.0)
    x = Fit(x, 0.0, 1.0, RANGE[0], RANGE[1])
    data.append(SLog2_to_lin(x))
WriteSPI1D('sony_slog2_10.spi1d', RANGE[0], RANGE[1], data)
