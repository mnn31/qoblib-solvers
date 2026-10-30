# LABS search

`lss.cpp` is a self avoiding walk search for low autocorrelation binary sequences,
after lssOrel (Boskovic, Brglez and Brest, Applied Soft Computing 2017).

    c++ -O3 -std=c++17 -march=native -o lss lss.cpp
    ./lss 99 skew out.sol 900 1 577
    ./lss 100 near101 out.sol 900 1 578 8 40

The arguments are length, mode, output, seconds, seed, target energy, walk factor
and polish margin in percent. `skew` walks over skew-symmetric sequences of odd
length. `near<M>` walks over skew-symmetric sequences of length M and cuts or
extends them to the wanted length, polishing the promising ones with single
flips. `full` is the same walk with single flips over all sequences.

All the values below were targets taken from the QOBLIB table, which holds
literature values. Nothing here beats the table. Where the best sequence of a
length is skew-symmetric or one step from it, the walk finds it in seconds; at the
other lengths it stops well short.

| length | table value | best from this search |
| ---: | ---: | ---: |
| 67 | 241 | 241 |
| 68 | 250 | 262 |
| 69 | 274 | 282 |
| 70 | 295 | 295 |
| 71 | 275 | 275 |
| 72 | 300 | 332 |
| 73 | 308 | 348 |
| 74 | 341 | 365 |
| 75 | 329 | 341 |
| 76 | 334 | 398 |
| 77 | 358 | 358 |
| 78 | 347 | 403 |
| 79 | 339 | 407 |
| 80 | 352 | 404 |
| 81 | 372 | 400 |
| 82 | 377 | 425 |
| 83 | 377 | 377 |
| 84 | 430 | 446 |
| 85 | 414 | 442 |
| 86 | 439 | 479 |
| 87 | 431 | 451 |
| 88 | 448 | 504 |
| 89 | 432 | 484 |
| 90 | 453 | 517 |
| 91 | 477 | 477 |
| 92 | 498 | 510 |
| 93 | 486 | 502 |
| 94 | 499 | 539 |
| 95 | 479 | 479 |
| 96 | 520 | 540 |
| 97 | 536 | 536 |
| 98 | 545 | 577 |
| 99 | 577 | 577 |
| 100 | 578 | 578 |
