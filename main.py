from lookup_tables import *
import numpy as np
import matplotlib.pyplot as plt


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
# +------------------------------+------+------+-----+------+
# | First Input Byte\Key Guesses | 0x00 | 0x01 | ... | 0xFF |
# +------------------------------+------+------+-----+------+
# | 0xCF                         |    2 |    1 | ... |    3 |
# | 0x1E                         |    3 |    3 | ... |    2 |
# | ...                          |  ... |  ... | ... |  ... |
# | 0xF4                         |    2 |    4 | ... |    6 |
# +------------------------------+------+------+-----+------+
# AES encrypts one byte at a time, so assuming each encryption of the full word takes the same amount of time, T,
# then the first byte of each word will be processed at the same time during the [0,T] timeframe
# For each row in the above table, there is a power trace for the full word that input byte belongs to
#
# Since we know that hamming weight is proportional to power usage, for every point in time, we correlate each column
# in the above table with the set of traces we have https://youtu.be/OlX-p4AGhWs?t=2887 and one of the columns will
# correlate the most. This means the key Guess for that column is likely to be correct for the first byte.

# Repeat until all of key is found

# (2^8 possible keys)

#plt.plot(power_traces[0])
#plt.show()


print len( textin)
print len(power_traces)



