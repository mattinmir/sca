from main import main
from official import official
import time

iterations = 50

main_time = 0
official_time = 0

for i in range(iterations):
    print ("Iteration {}:".format(i+1))
    start_time = time.time()
    main(do_print=False)
    time_taken = time.time() - start_time
    main_time += time_taken
    print ("\t Main: {} seconds".format(time_taken))

    start_time = time.time()
    official(do_print=False)
    time_taken = time.time() - start_time
    official_time += time_taken
    print ("\t Official: {} seconds".format(time_taken))

print ("Average over {} iterations:".format(iterations))
print ("\t Main: {} seconds".format(main_time/iterations))
print ("\t Official: {} seconds".format(official_time/iterations))
