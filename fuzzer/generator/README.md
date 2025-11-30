# DiveFuzz-Generator

This guide provides instructions on how to set up the environment, build the dependencies, and run generator.

## Requirements

Install the necessary Python packages using pip:

```shell
pip install pybind11
pip install tqdm
```

## Build Instructions

Follow these steps to clone the repository and build the components.

### 1. Clone Repository and Submodules

First, clone the main repository and initialize the required git submodules, which include the RISC-V ISA simulator (Spike).

```shell
git clone git@github.com:youzi27/DiveFuzz.git
cd DiveFuzz
git submodule update --init
```

### 2. Build the RISC-V ISA Simulator (Spike)

Enter the submodule directory to compile and install Spike.

**Note**: Ensure that the `$RISCV` environment variable is set and points to your RISC-V toolchain installation path.

```shell
cd riscv-isa-sim
mkdir build
cd build
../configure --prefix=$RISCV
make
make install # (optional)
cd ../.. 
# Return to the generator root directory (DiveFuzz/fuzzer/generator)
```

### 3. Build the Spike Wrapper

Compile the C++ dynamic library that interfaces with Spike.

```shell
cd spike_wrapper
make
cd ..
# Return to the generator root directory (DiveFuzz/fuzzer/generator)
```

## Environment Setup

To ensure that the system can locate the `spike` executable you just built, you need to add its path to your shell's `PATH` variable. A script is provided to handle this automatically.

From the generator's root directory (`DiveFuzz/fuzzer/generator`), run the following command:

```shell
source env.sh
```

**Important**: You will need to run `source env.sh` in every new terminal session before working on this project.

## Prerequisites Checklist

Before running the fuzzer, please ensure the following components are correctly installed and configured:

-   

     `spike` is installed and accessible via your `PATH`.

-   

     The RISC-V GNU toolchain (`riscv-gnu-unknown-*`) is installed.

## Usage Example

Navigate to the fuzzer's generator directory to run the main script.

```shell
cd DiveFuzz/fuzzer/generater
```

To see available options:

```shell
python ./main.py --help
```

To generate and mutate a test case with 10 instructions:

```shell
python ./main.py --generate -e --enable-ext --instr-number 10 --max-workers 20
```