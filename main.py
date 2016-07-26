
from lookup_tables import *
import numpy as np
import matplotlib.pyplot as plt
from pretty_print_weights import *


########################################################################################################################
#                                            Reading in Data
########################################################################################################################


dir = '/home/cwuser/chipwhisperer/projects/tmp/default_data/traces/'

# A list of lists of 16 (random) input data bytes that were sent into the device to be encrypted
textin = np.load(dir+'2016.07.25-10.56.46_textin.npy')

# Traces of power usage for the duration the corresponding input data was being encrypted on the device
power_traces = np.load(dir+'2016.07.25-10.56.46_traces.npy')

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

#plt.plot(power_traces[0])
#plt.show()

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

# pretty_print_weights(0, num_power_traces, textin, hamming_weights)


########################################################################################################################
#                                            Performing Correlation
########################################################################################################################

# For each subkey, correlation is given by:
#
# Original: https://wiki.newae.com/images/math/4/3/e/43ec93b3925401eb381eff776aef625e.png
# Mine: http://imgur.com/IfAuAz6
# Latex Code:  Correlation_{keyguess, time} =\frac{\sum_{traces}[(weight_{trace,keyguess} - \overline{weight_{keyguess}}) (power_{trace,time} - \overline{power_{time}})]}{\sqrt{\sum_{traces}(weight_{trace,keyguess} - \overline{weight_{keyguess}})^{2}\cdot \sum_{traces}(power_{trace,time} - \overline{power_{time}})^{2}}}

# One mean for each keyguess for each subkey over all traces
mean_weights = np.zeros((16, 256))

# One mean for each point in time
mean_powers = np.zeros(num_trace_readings)

for subkey in range(16):
    for keyguess in range(256):
        mean_weights[subkey][keyguess] = np.mean(hamming_weights[subkey][keyguess])

sum_power = 0.0
for time in range(num_trace_readings):
    for trace in range(num_power_traces):
        sum_power += power_traces[trace][time]
    mean_powers[time] = sum_power/num_power_traces

correlation_matrix = np.zeros((16, 256, num_trace_readings))
for subkey in range(1):
    for keyguess in range(256):
        for time in range(num_trace_readings):
            numerator = 0
            denominator1 = 0
            denominator2 = 0
            for trace in range(num_power_traces):
                numerator += (hamming_weights[subkey][keyguess][trace] - mean_weights[subkey][keyguess]) * (power_traces[trace][time] - mean_powers[time])

                denominator1 += (hamming_weights[subkey][keyguess][trace] - mean_weights[subkey][keyguess]) ** 2
                denominator2 += (power_traces[trace][time] - mean_powers[time]) ** 2

            denominator = np.sqrt(denominator1 * denominator2)
            correlation_matrix[subkey][keyguess][time] = numerator/denominator

print correlation_matrix

pass