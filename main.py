from __future__ import print_function

from lookup_tables import *
import numpy as np
# import matplotlib.pyplot as plt
from pretty_print_weights import *

########################################################################################################################
#                                            Reading in Data
########################################################################################################################


dir = '/home/cwuser/chipwhisperer/projects/tmp/default_data/traces/'

# A list of lists of 16 (random) input data bytes that were sent into the device to be encrypted
textin = np.load(dir + '2016.07.25-10.56.46_textin.npy')

# Traces of power usage for the duration the corresponding input data was being encrypted on the device
power_traces = np.load(dir + '2016.07.25-10.56.46_traces.npy')

# As a simplification, AES XORs the input with the private key one byte at a time, then substitutes the result for
# a new value via a lookup table (SBOX)
# For each line of input data, we will XOR each byte with every possible key, perform the SBOX substitution,
# and calculate the hamming weight (i.e. number of 1s) for each result https://youtu.be/OlX-p4AGhWs?t=2582
#
# THINK THIS IS HOW IT WORKS:
# Take the first byte of input data from each line as an example:
#                                <------2^8 Key guesses----->
# +------------------------------+------+------+-----+------+
# | First Input Byte\Key Guesses | 0x00 | 0x01 | ... | 0xFF |
# +------------------------------+------+------+-----+------+
# | 0xCF                         |    2 |    1 | ... |    3 |
# | 0x1E                         |    3 |    3 | ... |    2 |< Hamming weights after
# | ...                          |  ... |  ... | ... |  ... |  XOR and SBOX
# | 0xF4                         |    2 |    4 | ... |    6 |
# +------------------------------+------+------+-----+------+
# AES encrypts one byte at a time, so assuming each encryption of the full word takes the same amount of time, T,
# then the first byte of each word will be processed at the same time during the [0,T] timeframe
# For each row in the above table, there is a power trace for the full word that input byte belongs to.
#
# Since we know that hamming weight is proportional to power usage, for every point in time, we correlate each column
# in the above table with the set of traces we have https://youtu.be/OlX-p4AGhWs?t=2887 and one of the columns will
# correlate the most. This means the key Guess for that column is likely to be correct for the first byte.

# Repeat until all of key is found

# (2^8 Key guesses) * (16 Bytes of the key) * (N traces) = N*2^12
# N is typically < 2^7 -> max 2^19 + time for correlation
# vs brute forcing AES = 2^128 combinations = 3.4*10^38

# plt.plot(power_traces[0])
# plt.show()

num_power_traces = np.shape(power_traces)[0]
num_trace_readings = np.shape(power_traces)[1]

#
# print(num_power_traces)
# print (num_trace_readings)

# 16 subkeys, 256 key guesses, num_power_traces inputs for each subkey


#               \
#              16 tables
#                  \
#                   +--------------------------------------------------------+
#                   | Second Input Byte ...                                  |
#                   | +------------------------------+------+------+-----+------+
#                   | | First Input Byte\Key Guesses | 0x00 | 0x01 | ... | 0xFF |
#          ^        | +------------------------------+------+------+-----+------+
#          |        | | 0xCF                         |    2 |    1 | ... |    3 |
#  num_power_traces | | 0x1E                         |    3 |    3 | ... |    2 |
#          |        |_| ...                          |  ... |  ... | ... |  ... |
#          v          | 0xF4                         |    2 |    4 | ... |    6 |
#                     +------------------------------+------+------+-----+------+
#                                                    <------256 Key guesses----->

########################################################################################################################
#                                            Generating Hamming Weights
########################################################################################################################


dimensions = (16, 256, num_power_traces)
hamming_weights = np.zeros(dimensions, dtype=np.int)

for subkey in range(16):
    for keyguess in range(256):
        for trace in range(num_power_traces):
            encrypted = SBOX[textin[trace][subkey] ^ keyguess]
            hamming_weights[subkey][keyguess][trace] = HW[encrypted]

#pretty_print_weights(0, num_power_traces, textin, hamming_weights)


########################################################################################################################
#                                            Performing Correlation
########################################################################################################################

# For each subkey, correlation is given by:
#
# Original: https://wiki.newae.com/images/math/4/3/e/43ec93b3925401eb381eff776aef625e.png
# Mine: http://imgur.com/IfAuAz6
# Latex Code:  Correlation_{keyguess, time} =\frac{\sum_{traces}[(weight_{trace,keyguess} - \overline{weight_{keyguess}}) (power_{trace,time} - \overline{power_{time}})]}{\sqrt{\sum_{traces}(weight_{trace,keyguess} - \overline{weight_{keyguess}})^{2}\cdot \sum_{traces}(power_{trace,time} - \overline{power_{time}})^{2}}}
# This equation is only for ONE subkey, so needs to be repeated 16 times



# power_traces[trace][time]
#
#          time0  time1  time2  ...
# trace 0 ------|------|------|-->
# trace 1 ------|------|------|-->
# trace 2 ------|------|------|-->#
#
# np.mean (axis=None) flattens array and computes mean
# np.mean (axis=0) returns average for each time over all traces
# np.mean (axis=1) returns average for each trace over all times


# One mean for each keyguess for each subkey over all traces
mean_weights = np.mean(hamming_weights, axis=2, dtype=np.float64)

# One mean for each point in time over all traces
mean_powers = np.mean(power_traces, axis=0, dtype=np.float64)


correlation_matrix = np.zeros((16, 256, num_trace_readings))
highest_coefficient = np.zeros((16, 256))
full_key = [0] * 16 # np.zeros(16, dtype=np.int64)

for subkey in range(16):
    for keyguess in range(256):
        #for time in range(num_trace_readings):
        numerators = np.zeros(num_trace_readings)
        denominator1s = np.zeros(num_trace_readings) # All same value, maybe use single point var?
        denominator2s = np.zeros(num_trace_readings)
        for trace in range(num_power_traces):
            # weight_diff is the (weight_{trace,keyguess} - \overline{weight_{keyguess}}) term in the equation
            # Since it is independent of time, it is just a single value for the whole trace
            weight_diff = hamming_weights[subkey][keyguess][trace] - mean_weights[subkey][keyguess]

            # power_diff is the (power_{trace,time} - \overline{power_{time}}) term in the equation
            # Since is is time-dependent, it is an array of size num_power_traces, one value for each time in each trace
            power_diff_array = power_traces[trace] - mean_powers

            # Building a list of each time point's numerator for this subkey/keyguess
            numerators += weight_diff * power_diff_array

            # Multiplying by itself is faster than using power function
            denominator1s += weight_diff * weight_diff
            denominator2s += power_diff_array * power_diff_array
            #numerator += (hamming_weights[subkey][keyguess][trace] - mean_weights[subkey][keyguess]) * (
           # power_traces[trace][time] - mean_powers[time])

            #denominator1s += (hamming_weights[subkey][keyguess][trace] - mean_weights[subkey][keyguess]) ** 2
            #denominator2s += (power_traces[trace][time] - mean_powers[time]) ** 2

        denominators = np.sqrt(denominator1s * denominator2s)

        # putting into correlation matrix the correlation coefficients for that subkey/keyguess at every point in time
        correlation_matrix[subkey][keyguess] = numerators / denominators

        # For each keyguess, record its correlation coefficient at the time at which it was most correlated
        # It doesn't matter that this mixes up the time data because there should only be one keyguess at one point in
        # time that has a high coefficent for the subkey
        highest_coefficient[subkey][keyguess] = max(abs(correlation_matrix[subkey][keyguess]))

    # Return the index of the largest value in highest_coefficient, which corresponds to the subkey value
    full_key[subkey] = np.asscalar(np.argmax(highest_coefficient[subkey]))
    print ("Got key byte", str(subkey) + ":", hex(full_key[subkey]))

#np.set_printoptions(formatter={'int':hex})

print ("Best guess at full key: ")
print (full_key)
for subkey in full_key:
    print (hex(subkey)[2:], end="")

pass
