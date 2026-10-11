# Results on the 102 open sports instances

Solved: 23 of 102. One run per instance, OR-Tools CP-SAT, 16 workers, one instance at a time on the RunPod EPYC 9655 pod (16 vCPUs). Every solved timetable passed both the independent checker and the official RobinX validator.

| instance | teams | slots | phased | hard constraints | status | wall s | time limit | RobinX infeasibility | RobinX soft penalty |
| :--- | ---: | ---: | :---: | ---: | :--- | ---: | ---: | ---: | ---: |
| Addition_000_NoSoft | | | | | not run | | | | |
| Addition_003_NoSoft | | | | | not run | | | | |
| Addition_005_NoSoft | | | | | not run | | | | |
| Addition_007_NoSoft | | | | | not run | | | | |
| Addition_015_NoSoft | | | | | not run | | | | |
| Addition_016_NoSoft | | | | | not run | | | | |
| Addition_018_NoSoft | | | | | not run | | | | |
| Addition_020_NoSoft | | | | | not run | | | | |
| Addition_024_Medium | | | | | not run | | | | |
| Addition_024_NoSoft | | | | | not run | | | | |
| Addition_025_Medium | | | | | not run | | | | |
| Addition_025_NoSoft | | | | | not run | | | | |
| Addition_027_Medium | | | | | not run | | | | |
| Addition_027_NoSoft | | | | | not run | | | | |
| Addition_028_NoSoft | | | | | not run | | | | |
| Addition_029_NoSoft | | | | | not run | | | | |
| Addition_030_NoSoft | | | | | not run | | | | |
| Addition_032_NoSoft | | | | | not run | | | | |
| Addition_034_NoSoft | | | | | not run | | | | |
| Addition_035_NoSoft | | | | | not run | | | | |
| Addition_043_NoSoft | | | | | not run | | | | |
| Addition_044_NoSoft | | | | | not run | | | | |
| Addition_046_NoSoft | | | | | not run | | | | |
| Addition_047_Medium | 12 | 22 | yes | 120 | unknown | 600.1 | 600 |  |  |
| Addition_047_NoSoft | | | | | not run | | | | |
| Addition_048_NoSoft | | | | | not run | | | | |
| Addition_050_NoSoft | | | | | not run | | | | |
| Addition_052_NoSoft | | | | | not run | | | | |
| Addition_064_NoSoft | | | | | not run | | | | |
| Addition_066_NoSoft | | | | | not run | | | | |
| Addition_067_NoSoft | | | | | not run | | | | |
| Addition_068_NoSoft | | | | | not run | | | | |
| Addition_069_NoSoft | | | | | not run | | | | |
| Addition_070_NoSoft | | | | | not run | | | | |
| Addition_082_NoSoft | 18 | 34 | yes | 97 | unknown | 600.4 | 600 |  |  |
| Addition_083_NoSoft | | | | | not run | | | | |
| Addition_085_NoSoft | | | | | not run | | | | |
| Addition_090_NoSoft | | | | | not run | | | | |
| Addition_100_NoSoft | | | | | not run | | | | |
| Addition_104_NoSoft | | | | | not run | | | | |
| Addition_105_Medium | | | | | not run | | | | |
| Addition_105_NoSoft | | | | | not run | | | | |
| Addition_107_NoSoft | | | | | not run | | | | |
| Addition_109_NoSoft | | | | | not run | | | | |
| Addition_110_NoSoft | | | | | not run | | | | |
| Addition_111_NoSoft | | | | | not run | | | | |
| Addition_128_Medium | | | | | not run | | | | |
| Addition_128_NoSoft | | | | | not run | | | | |
| Addition_129_NoSoft | | | | | not run | | | | |
| Addition_130_NoSoft | | | | | not run | | | | |
| Addition_132_NoSoft | | | | | not run | | | | |
| Addition_133_NoSoft | | | | | not run | | | | |
| Addition_152_NoSoft | | | | | not run | | | | |
| Early_005_NoSoft | | | | | not run | | | | |
| Early_010_NoSoft | | | | | not run | | | | |
| ITC2021_Early_01 | | | | | not run | | | | |
| ITC2021_Early_02 | 16 | 30 | yes | 53 | unknown | 600.2 | 600 |  |  |
| ITC2021_Early_03 | 16 | 30 | yes | 148 | feasible | 0.3 | 600 | 0 | 4998 |
| ITC2021_Early_04 | | | | | not run | | | | |
| ITC2021_Early_05 | | | | | not run | | | | |
| ITC2021_Early_06 | | | | | not run | | | | |
| ITC2021_Early_07 | | | | | not run | | | | |
| ITC2021_Early_08 | 18 | 34 | no | 70 | feasible | 0.4 | 600 | 0 | 5616 |
| ITC2021_Early_09 | 18 | 34 | no | 90 | feasible | 0.4 | 600 |  |  |
| ITC2021_Early_10 | | | | | not run | | | | |
| ITC2021_Early_11 | | | | | not run | | | | |
| ITC2021_Early_12 | 20 | 38 | yes | 179 | feasible | 22.9 | 600 |  |  |
| ITC2021_Early_13 | | | | | not run | | | | |
| ITC2021_Early_14 | 20 | 38 | no | 56 | feasible | 0.6 | 600 | 0 | 11303 |
| ITC2021_Early_15 | | | | | not run | | | | |
| ITC2021_Late_01 | 16 | 30 | no | 235 | feasible | 84.7 | 600 | 0 | 3500 |
| ITC2021_Late_02 | | | | | not run | | | | |
| ITC2021_Late_03 | 16 | 30 | no | 127 | feasible | 1.1 | 600 | 0 | 8607 |
| ITC2021_Late_04 | 18 | 34 | yes | 96 | feasible | 0.5 | 600 | 0 | 1385 |
| ITC2021_Late_05 | | | | | not run | | | | |
| ITC2021_Late_06 | 18 | 34 | yes | 163 | feasible | 23.2 | 600 | 0 | 4061 |
| ITC2021_Late_07 | | | | | not run | | | | |
| ITC2021_Late_08 | 18 | 34 | yes | 110 | feasible | 0.5 | 600 | 0 | 4545 |
| ITC2021_Late_09 | 18 | 34 | no | 102 | feasible | 4.0 | 600 | 0 | 3233 |
| ITC2021_Late_10 | | | | | not run | | | | |
| ITC2021_Late_11 | | | | | not run | | | | |
| ITC2021_Late_12 | | | | | not run | | | | |
| ITC2021_Late_13 | 20 | 38 | no | 169 | feasible | 4.7 | 600 | 0 | 7977 |
| ITC2021_Late_14 | 20 | 38 | no | 116 | feasible | 16.3 | 600 | 0 | 3787 |
| ITC2021_Late_15 | 20 | 38 | no | 51 | feasible | 0.6 | 600 | 0 | 9335 |
| ITC2021_Middle_01 | | | | | not run | | | | |
| ITC2021_Middle_02 | | | | | not run | | | | |
| ITC2021_Middle_03 | | | | | not run | | | | |
| ITC2021_Middle_04 | 18 | 34 | yes | 97 | feasible | 1.5 | 600 | 0 | 328 |
| ITC2021_Middle_05 | 18 | 34 | yes | 151 | feasible | 0.5 | 600 | 0 | 7782 |
| ITC2021_Middle_06 | 18 | 34 | yes | 162 | feasible | 6.2 | 600 | 0 | 3560 |
| ITC2021_Middle_07 | 18 | 34 | no | 141 | feasible | 1.3 | 600 | 0 | 9009 |
| ITC2021_Middle_08 | 18 | 34 | no | 62 | feasible | 1.7 | 600 |  |  |
| ITC2021_Middle_09 | 18 | 34 | no | 94 | feasible | 1.2 | 600 | 0 | 3315 |
| ITC2021_Middle_10 | | | | | not run | | | | |
| ITC2021_Middle_11 | | | | | not run | | | | |
| ITC2021_Middle_12 | 20 | 38 | yes | 63 | feasible | 3.5 | 600 | 0 | 4609 |
| ITC2021_Middle_13 | 20 | 38 | no | 219 | feasible | 3.2 | 600 | 0 | 6544 |
| ITC2021_Middle_14 | | | | | not run | | | | |
| ITC2021_Middle_15 | 20 | 38 | no | 95 | feasible | 0.6 | 600 | 0 | 8251 |
| Late_005_NoSoft | | | | | not run | | | | |
| Middle_002_NoSoft | | | | | not run | | | | |

Unsolved (79): Addition_000_NoSoft, Addition_003_NoSoft, Addition_005_NoSoft, Addition_007_NoSoft, Addition_015_NoSoft, Addition_016_NoSoft, Addition_018_NoSoft, Addition_020_NoSoft, Addition_024_Medium, Addition_024_NoSoft, Addition_025_Medium, Addition_025_NoSoft, Addition_027_Medium, Addition_027_NoSoft, Addition_028_NoSoft, Addition_029_NoSoft, Addition_030_NoSoft, Addition_032_NoSoft, Addition_034_NoSoft, Addition_035_NoSoft, Addition_043_NoSoft, Addition_044_NoSoft, Addition_046_NoSoft, Addition_047_Medium, Addition_047_NoSoft, Addition_048_NoSoft, Addition_050_NoSoft, Addition_052_NoSoft, Addition_064_NoSoft, Addition_066_NoSoft, Addition_067_NoSoft, Addition_068_NoSoft, Addition_069_NoSoft, Addition_070_NoSoft, Addition_082_NoSoft, Addition_083_NoSoft, Addition_085_NoSoft, Addition_090_NoSoft, Addition_100_NoSoft, Addition_104_NoSoft, Addition_105_Medium, Addition_105_NoSoft, Addition_107_NoSoft, Addition_109_NoSoft, Addition_110_NoSoft, Addition_111_NoSoft, Addition_128_Medium, Addition_128_NoSoft, Addition_129_NoSoft, Addition_130_NoSoft, Addition_132_NoSoft, Addition_133_NoSoft, Addition_152_NoSoft, Early_005_NoSoft, Early_010_NoSoft, ITC2021_Early_01, ITC2021_Early_02, ITC2021_Early_04, ITC2021_Early_05, ITC2021_Early_06, ITC2021_Early_07, ITC2021_Early_10, ITC2021_Early_11, ITC2021_Early_13, ITC2021_Early_15, ITC2021_Late_02, ITC2021_Late_05, ITC2021_Late_07, ITC2021_Late_10, ITC2021_Late_11, ITC2021_Late_12, ITC2021_Middle_01, ITC2021_Middle_02, ITC2021_Middle_03, ITC2021_Middle_10, ITC2021_Middle_11, ITC2021_Middle_14, Late_005_NoSoft, Middle_002_NoSoft
