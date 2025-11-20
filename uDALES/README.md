*****************************************************
** Some instructions to run the cases on DelftBlue **
*****************************************************

--- You will need to edit the following fields in the `submit.sh` script
max_wait_time [seconds] - This is the maximum wait time allowed for pre-processing 
uDALES_HOME [string] - This is the full path to the location where uDALES is compiled

-- You will need to edit the following fields in the gen_cases.sh script

angles [array of string] - Comma seperated angles corresponding to the geometry rotations in degrees
geo_location [string] - Location where the geometry is setup
geo_prefix [string] - Prefix of the geometry name (e.g., campus for files named campus_120.stl)
submit_jobs [1 or 0] - Integer flag to submit jobs or only generate directories
exp_start_num [integer] - Integer value that corresponds to the starting angle
driver_exp_num [integer] - Experiment number of the driver simulations, typically == 1

*****************************************************
Example of case directory layout

```
README.md  coarse_les_geometry  config.sh  driver_files  gen_cases.sh  namoptions  submit.sh
```

In this example, `coarse_les_geometry` is where the geometry is stored names as `campus_0.59.stl`, `campus_1.82.stl`, and so on.
The driver files are located within `driver_files` which contains the following files, where the decomposition corresponds to
4 x 2 decomposition i.e., procy = 2 that is the two decomposition.
```
tdriver_000.001  udriver_000.001  udriver_001.001  vdriver_000.001  vdriver_001.001  wdriver_000.001  wdriver_001.001
```
The `config.sh` is the template file that will be used/copied for each of the case
The `namoptions` is the template file that will be used for the preprocessing and final simulation
