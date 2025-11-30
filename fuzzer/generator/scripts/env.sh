#!/bin/bash

# This script is used to set the environment variables required for DiveFuzz.
# Please execute it in the root directory of the project using the 'source env.sh' command.
# Build the path where the spike executable file is located based on the generator root directory.
SPIKE_DIR="$(pwd)/../../ref/riscv-isa-sim-adapter/build"

# Check if the build directory of spike exists. If it doesn't, an error prompt will be given.
if [ ! -d "$SPIKE_DIR" ]; then
    echo "Error: The Spike build directory was not found: ${SPIKE_DIR}"
    echo "Please confirm that you have completed the compilation steps as instructed in the README."
    return 1
fi

# Check if the spike executable file exists
if [ ! -f "${SPIKE_DIR}/spike" ]; then
    echo "Error: The 'spike' executable file was not found at:${SPIKE_DIR}"
    echo "Please confirm whether the compilation has been successfully completed."
    return 1
fi

# Add the PATH of spike to the front of the PATH environment variable to ensure that the version compiled for this project is used first.
export PATH="${SPIKE_DIR}:${PATH}"

echo "The environment has been set up successfully!"
echo "The following paths have been added to the PATH environment variable:"
echo "${SPIKE_DIR}"

export NOOP_HOME=$(pwd)/../../../dut/XiangShan
export SPIKE_HOME=$(pwd)/../../../dut/XiangShan/riscv-isa-sim