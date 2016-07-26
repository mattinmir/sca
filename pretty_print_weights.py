from __future__ import print_function


def pretty_print_weights(subkey, num_power_traces, textin, hamming_weights):
    print('\t', end="")
    for keyguess in range(256):
        print ('\t' + "0x{:02x}".format(keyguess)[2:], end="")

    print('\n')

    for trace in range(num_power_traces):
        print("0x{:02x}".format(textin[trace][subkey]), end="")
        for keyguess in range(256):
            print('\t' + str(hamming_weights[subkey][keyguess][trace]), end="")
        print('\n')