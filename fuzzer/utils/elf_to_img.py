# Copyright (c) 2024-2025 Institute of Information Engineering, Chinese Academy of Sciences
# 
# DiveFuzz is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#          http://license.coscl.org.cn/MulanPSL2
# 
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# 
# See the Mulan PSL v2 for more details.

import os
import subprocess
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

def process_file(filename, folder_path, img_folder, elf_folder):
    """
    Process a single assembly file.

    Parameters:
    filename: File name
    folder_path: Path to the folder where the original file is located
    img_folder: Directory where the generated img file will be stored
    elf_folder: Directory where the generated elf file will be stored
    """

    base_name = os.path.splitext(filename)[0]
    source_path = os.path.join(folder_path, filename)

    object_file = os.path.join(folder_path, base_name + '.o')
    elf_file = os.path.join(elf_folder, base_name + '.elf')
    img_file = os.path.join(img_folder, base_name + '.img')


    link_dir = Path(__file__).parent.parent / 'generator' / 'reg_analyzer' / 'linker' / 'link.ld'
    subprocess.run(['riscv64-unknown-elf-as', '-march=rv64g_c_v_zicsr_zifencei_zfh_zba_zbb_zbkc_zbc_zbkb_zbs_zmmul_zknh_zkne_zknd_zbkx_zfhmin', '-c', source_path, '-o', object_file])
    subprocess.run(['riscv64-unknown-elf-ld', '-T', link_dir, object_file, '-o', elf_file])
    subprocess.run(['riscv64-unknown-elf-objcopy', '-O', 'binary', elf_file, img_file])

    # Delete .o files
    if os.path.exists(object_file):
        os.remove(object_file)
    

def process_file_for_spec(filename, folder_path, img_folder, elf_folder):
    """
    Process a single assembly file.

    Parameters:
    filename: File name
    folder_path: Path to the folder where the original file is located
    img_folder: Directory where the generated img file will be stored
    elf_folder: Directory where the generated elf file will be stored
    """

    base_name = os.path.splitext(filename)[0]
    source_path = os.path.join(folder_path, filename)

    object_file = os.path.join(folder_path, base_name + '.o')
    elf_file = os.path.join(elf_folder, base_name + '.elf')
    img_file = os.path.join(img_folder, base_name + '.img')

    link_dir = Path(__file__).parent.parent / 'generator' / 'reg_analyzer' / 'linker' / 'link.ld'
    subprocess.run(['riscv64-unknown-elf-gcc', '-march=rv64g_c_v_zicsr_zifencei_zfh_zba_zbb_zbkc_zbc_zbkb_zbs_zmmul_zknh_zkne_zknd_zbkx_zfhmin', '-c', source_path, '-o', object_file])

    subprocess.run(['riscv64-unknown-elf-ld', '-T', link_dir, object_file, '-o', elf_file])
    subprocess.run(['riscv64-unknown-elf-objcopy', '-O', 'binary', elf_file, img_file])

    if os.path.exists(object_file):
        os.remove(object_file)



    

def process_assembly_files(folder_path):
    """
    Process all assembly files (.S) in the specified folder.

    Parameters:
    folder_path: Path to the folder to be processed.
    """
    grandparent_folder = os.path.dirname(os.path.dirname(folder_path))

    img_folder = os.path.join(folder_path, 'img_file')
    os.makedirs(img_folder, exist_ok=True)

    elf_folder = os.path.join(folder_path, 'elf_file')
    os.makedirs(elf_folder, exist_ok=True)

    assembly_files = [f for f in os.listdir(folder_path) if f.endswith('.S')]

    # Use a thread pool to process files
    with ThreadPoolExecutor() as executor:
        list(tqdm(executor.map(process_file, assembly_files, [folder_path]*len(assembly_files), [img_folder]*len(assembly_files), \
                            [elf_folder]*len(assembly_files)), total=len(assembly_files), desc="Processing assembly files"))

    print("Successfully generated img files!")



def process_assembly_files_to_timeout(folder_path):
    """
    通过

    """
    parent_folder = os.path.dirname(folder_path)

    img_folder = os.path.join(parent_folder, 're_img_file')
    os.makedirs(img_folder, exist_ok=True)

    elf_folder = os.path.join(parent_folder, 're_elf_file')
    os.makedirs(elf_folder, exist_ok=True)

    assembly_files = [f for f in os.listdir(folder_path) if f.endswith('.S')]

    # Use a thread pool to process files
    with ThreadPoolExecutor() as executor:
        list(tqdm(executor.map(process_file, assembly_files, [folder_path]*len(assembly_files), [img_folder]*len(assembly_files), \
                            [elf_folder]*len(assembly_files)), total=len(assembly_files), desc="Processing assembly files"))

    print("Successfully generated img files!")

def process_assembly_files_to_force_mm(folder_path):
    """
    Force execution in M-mode
    """
    parent_folder = os.path.dirname(folder_path)

    img_folder = os.path.join(parent_folder, 're_img_file_mm')
    os.makedirs(img_folder, exist_ok=True)

    elf_folder = os.path.join(parent_folder, 're_elf_file_mm')
    os.makedirs(elf_folder, exist_ok=True)

    assembly_files = [f for f in os.listdir(folder_path) if f.endswith('.S')]

    # Use a thread pool to process files
    with ThreadPoolExecutor() as executor:
        list(tqdm(executor.map(process_file, assembly_files, [folder_path]*len(assembly_files), [img_folder]*len(assembly_files), \
                            [elf_folder]*len(assembly_files)), total=len(assembly_files), desc="Processing assembly files"))

    print("Successfully generated img files!")

def process_assembly_files_for_spec(folder_path):

    parent_folder = os.path.dirname(folder_path)

    img_folder = os.path.join(parent_folder, 'spec_issue_em_img')
    os.makedirs(img_folder, exist_ok=True)

    elf_folder = os.path.join(parent_folder, 'spec_issue_em_elf_file')
    os.makedirs(elf_folder, exist_ok=True)

    assembly_files = [f for f in os.listdir(folder_path) if f.endswith('.S')]

    with ThreadPoolExecutor() as executor:
        list(tqdm(executor.map(process_file, assembly_files, [folder_path]*len(assembly_files), \
                [img_folder]*len(assembly_files), [elf_folder]*len(assembly_files)), \
                    total=len(assembly_files), desc="Processing assembly files"))

    print("\033[94mAssembly file has been fixed!\033[0m")


def process_assembly_files_debug(folder_path):
    """
    Process all assembly files (.S) in the specified folder.

    Parameters:
    folder_path: Path to the folder that needs to be processed.
    """

    parent_folder = os.path.dirname(folder_path)

    img_folder = os.path.join(folder_path, 'img_file')
    os.makedirs(img_folder, exist_ok=True)

    elf_folder = os.path.join(folder_path, 'elf_file')
    os.makedirs(elf_folder, exist_ok=True)

    assembly_files = [f for f in os.listdir(folder_path) if f.endswith('.S')]


    with ThreadPoolExecutor() as executor:

        list(tqdm(executor.map(process_file, assembly_files, [folder_path]*len(assembly_files), [img_folder]*len(assembly_files), [elf_folder]*len(assembly_files)), total=len(assembly_files), desc="Processing assembly files"))

    print("Successfully generated img files!")


def process_file_rv32(filename, folder_path, elf_folder):
    """
    Process a single assembly file.

    Parameters:
    filename: File name
    folder_path: Path to the folder where the original file is located
    img_folder: Path where the generated img file will be stored
    elf_folder: Path where the generated elf file will be stored
    """
    base_name = os.path.splitext(filename)[0]
    source_path = os.path.join(folder_path, filename)

    object_file = os.path.join(folder_path, base_name + '.o')
    elf_file = os.path.join(elf_folder, base_name + '.elf')


    subprocess.run(['gcc/rv32imbc/bin/riscv32-unknown-elf-gcc', '-march=rv32g_b', '-c', source_path, '-o', object_file])

    subprocess.run(['gcc/rv32imbc/bin/riscv32-unknown-elf-ld', '-T', 'fuzzer/linker/link32.ld', object_file, '-o', elf_file])


    if os.path.exists(object_file):
        os.remove(object_file)

def process_assembly_files_rv32(folder_path):
    """
    Process all assembly files (.S) in the specified folder.

    Parameters:
    folder_path: Path to the folder that needs to be processed.
    """

    grandparent_folder = os.path.dirname(os.path.dirname(folder_path))



    elf_folder = os.path.join(grandparent_folder, 'elf_file')
    os.makedirs(elf_folder, exist_ok=True)

    assembly_files = [f for f in os.listdir(folder_path) if f.endswith('.S')]

    with ThreadPoolExecutor() as executor:

        list(tqdm(executor.map(process_file_rv32, assembly_files, [folder_path]*len(assembly_files),  \
                            [elf_folder]*len(assembly_files)), total=len(assembly_files), desc="Processing assembly files"))

    print("Successfully generated img files!")

# if __name__ == '__main__':
    #process_assembly_files('/DiveFuzz/fuzzer/generator/out-seeds')