# DiveFuzz

DiveFuzz is a diversified instruction generation approach designed specifically for RISC-V CPUs. Its core idea is to drive testing through dynamically diversified instruction write-back values, enabling effective exploration of CPU states. More details can be found in the [paper](https://dl.acm.org/doi/10.1145/3719027.3765167). In addition, the project is under active development and will continue to incorporate new extensions and features beyond those described in the paper.


## Get Start


Clone the main repository

```
git clone https://github.com/In2Sec/DiveFuzz
cd DiveFuzz
```

Clone the runtime-diversified version of riscv-isa-sim adapted for DiveFuzz as a `git submodule`

```
git submodule init ref/riscv-isa-sim-adapter
git submodule update ref/riscv-isa-sim-adapter
```

Navigate to the dut directory and select your target RISC-V CPU for testing. **If you already have the target existing, you can skip this step.**

```
cd dut

# Example: XiangShan
git submodule init XiangShan
```

## Requirements

### RISC-V toolchain

*DiveFuzz using RISC-V toolchain to generate test cases. For base usage, the following dependencies are required: `riscv64-unknown-elf-*`*

You can obtain the toolchain by following the instructions [here](https://github.com/riscv-collab/riscv-gnu-toolchain). We need the `newlib` version of the toolchain, which prefixes with `riscv64-unknown-elf-`, designed for embedded applications and bare metal development.

We recommend version 2025.11.27; Older versions may have issues with certain extensions not being supported.


### Spike RISC-V ISA simulator
*DiveFuzz's diverse test generation capability relies on the Spike RISC-V ISA simulator.*

The following dependencies are required to install Spike on Debian-based systems:

```
apt-get install device-tree-compiler libboost-regex-dev libboost-system-dev
```

Enter the submodule directory (`ref/riscv-isa-sim-adapter` and `ref/riscv-isa-sim`) to compile and install Spike.

```shell
cd riscv-isa-sim-adapter # or cd riscv-isa-sim
mkdir build
cd build
../configure
make
```

### Python libraries

*DiveFuzz requires the installation of Python, pip, and the necessary Python libraries.*

Assumes you have Python and pip installed, with a Python version **of** 3.10 **or newer**.Then install the necessary Python packages using pip:

```shell
cd DiveFuzz
pip install -r requirements.txt
```

Then, build the Spike C/C++ and python wrapper

```shell
cd ref/riscv-isa-sim-adapter/spike_engine
make
```

## Environment Setup

### REF Configuration

To ensure that the system can locate the `spike` executable you just built, you need to add its path to your shell's `PATH` variable.

```shell
# make sure you are in the DiveFuzz root directory, then run:
export PATH="$(pwd)/riscv-isa-sim-adapter/build:${PATH}"
```

**Important**: You need to re-run this command every time you open a new terminal session.

### DUT Configuration

Enter your DUT directory and build the emulator with:
```shell
export NOOP_HOME="$(pwd)"
make emu   
```



## Usage Example

`fuzzer/demo.yaml.dev` is the configuration file for DiveFuzz. You can modify it to fit your needs. Then rename it to `your_test.yaml` and place it in the `fuzzer` directory.

```yaml
# Device under test target config
dut_target:
# The name of the DUT target
- name: "XiangShan KMH DiveFuzz Inst 100"
  # How many threads to use
  threads: 16
  # The version of the DUT target
  version: commit:718a93f
  # Spike or NEMU or None
  diff_ref: Spike
  # The path of the DUT
  emu_path: /path/many_version/718a93f/XiangShan
  # Tell DiveFuzz how to run the DUT
  # notice: $1 is the input file
  cmd: ./build/emu -i $1  --diff /path/dut_fuzz/dut_instance/xs-env/XiangShan/ready-to-run/riscv64-spike-so

seeds:
- name: divefuzz_ins_10
  # Type of input for the seed. Allowed values: dir (directory input), divefuzz (DiveFuzz-formatted input), or leave unset for a single test case.
  input: divefuzz
  divefuzz:
    # TODO: Only generate seeds, do not deliver to DUT
    gen_only: false
    # parallelism
    threads: 128
    # Whether to enable error elimination
    dive_enable: true
    # Generate or mutate
    mode: generate
    # Path to store seeds after generation/mutation
    seeds_output: /path/seeds_output_inst_100

    # The following features are only effective when the mode is set to generate
    # Number of seeds to generate
    seeds_num: 4
    # Number of instructions for each seed
    ins_num: 100
    # Special instruction generation for cva6
    is_cva6: false
    # Special instruction generation for rv32
    is_rv32: false
    template_type: 'xiangshan'
    # # The following features are only effective when the mode is set to mutate
    # # In mutation mode, the path to the initial corpus
    # mutate_input: /path/seeds_output_inst_100
    # # Enable instruction expansion mutation
    # enable_extension: true
    # # Excluded instruction extensions
    # exclude_extension: ['zicsr']
- name: dir_seeds
  # directory input
  input: dir
  # filter seeds by file suffix
  suffix: elf
  # the path of the directory
  path: /path/riscv_a

- name: seed_0
  # the path of the single test case
  path: /path/riscv_b/seed_0.elf

```


When you are ready to run DiveFuzz, run the following command:

```shell
cd fuzzer/
python run_dut.py --config your_test.yaml
```


After the execution is complete, you can find the results in the `outputs` directory.

DiveFuzz implements a three-tier logging system
1. **DiveFuzz runtime logs**  
   Directly output during execution of `run_dut.py`
   
2. **Seed configuration logs**  
   Stored at: `outputs/{configuration_file}-{seed_profile_name}.log`, like `outputs/your_test_divefuzz_ins_10.log`

3. **Per-seed execution logs**  
   Stored at: `outputs/{configuration_file}-{seed_profile_name}_{seed_basename}.log`, like `outputs/your_test-divefuzz_ins_10_seed_0_.elf.log`
