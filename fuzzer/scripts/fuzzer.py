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



# This script is used to test a specific version of the CPU.
import os
import subprocess
import shutil
import argparse
import sys
from nts_run import nts_run_command_and_check, get_spec_issue
from src.logger import Logger
from src.process_bar import show_progress
from src.log_analyze import remove_lines_and_count
import nts_run# to get global value
import threading
from concurrent.futures import ThreadPoolExecutor,as_completed
import re 
from bug_fliter_rkt import fliter_known_bug
import psutil

from utils.spec_em_nts import rewrite_asm_files

from xs_run import xs_run_command_and_check, get_spec_issue

class CommandThread(threading.Thread):
    def __init__(self, img_file, emu_directory, dest_folder):
        threading.Thread.__init__(self)
        self.img_file = img_file
        self.emu_directory = emu_directory
        self.dest_folder = dest_folder

    def run(self):
        run_command_and_check(self.img_file, self.emu_directory, self.dest_folder)

class CommandThread_Nutshell(threading.Thread):
    def __init__(self, img_file, emu_directory, dest_folder):
        threading.Thread.__init__(self)
        self.img_file = img_file
        self.emu_directory = emu_directory
        self.dest_folder = dest_folder

    def run(self):
        nts_run_command_and_check(self.img_file, self.emu_directory, self.dest_folder)



def run_command_and_check(img_file, emu_directory, dest_folder):

    command = f"{emu_directory}/emu -b 0 -e 0 -i {img_file}"

    img_file_name = os.path.basename(img_file)
    timeout = 30 
    try:
        process = subprocess.Popen(command, shell=True, \
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate(timeout=timeout)  
    except subprocess.TimeoutExpired:
        parent = psutil.Process(process.pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
        abd_dir_name = "time_out"
        abd_dir_path = os.path.join(dest_folder, abd_dir_name)
        os.makedirs(abd_dir_path, exist_ok=True)
        shutil.copy(img_file, abd_dir_path)
        print(f"Timeout! Copied {img_file} to {abd_dir_path}\n")
        return  

    bug_number = 0 

    failed_dir_name = "failed_finished" # This is used to store seeds that ended with errors
    failed_dir_path = os.path.join(dest_folder, failed_dir_name)
    os.makedirs(failed_dir_path, exist_ok=True)

    positive_bug_path = "positive_bug" # Give priority to handling the bugs here
    positive_bug_dir_path = os.path.join(dest_folder, positive_bug_path)
    os.makedirs(positive_bug_dir_path, exist_ok=True)

    different_count = 0
    bug_flag = True
    first_diff = False
    success_end = False
    for line in stdout.decode().split('\n') + stderr.decode().split('\n'):
        if 'different at pc' in line or 'Mismatch' in line:
            if not first_diff:
                print(f"\033[91mBug report:\033[0m","\t",img_file_name)
                first_diff = True
                bug_flag = False
            different_count += 1
            print(f"\033[91m\t{line}\033[0m")  
        if 'instrCnt =' in line:
            instrCnt_value = line.split('=')[1].strip()
            if first_diff:
                print(f"\tinstrCnt value: {instrCnt_value}")
        if 'wfi <--' in line:
            success_end = True

        if '<--' in line:
            bug_number = fliter_known_bug(line)

    numbers = re.findall(r'\d+', instrCnt_value) 
    instrCnt_numbers = int("".join(numbers))

    if  bug_flag:
        print(f"PASSED!{img_file}")
        print(f"\tinstrCnt value: {instrCnt_value}")

    if success_end:
        print("\033[32m\tSuccessfully Finished!\033[0m")
    else:
        if bug_number == 1 and instrCnt_numbers > 40000:
            print(f"\033[96m\tknown_bug_1!\n\033[0m")    
            known_bug_1 = "known_bug_1" 
            known_bug_1_path = os.path.join(dest_folder, known_bug_1)
            os.makedirs(known_bug_1_path, exist_ok=True)
            shutil.copy(img_file, known_bug_1_path)
        elif instrCnt_numbers > 40000:
        
            print(f"\033[96m\tknown_bug_2!\n\033[0m")
            known_bug_2 = "known_bug_2" 
            known_bug_2_path = os.path.join(dest_folder, known_bug_2)
            os.makedirs(known_bug_2_path, exist_ok=True)
            shutil.copy(img_file, known_bug_2_path)
        else:
            print(f"\033[91m\tFaild Finished!\033[0m")
            shutil.copy(img_file, failed_dir_path)
    if success_end and not bug_flag:
        shutil.copy(img_file, positive_bug_dir_path)


def main():
    parser = argparse.ArgumentParser(description='Run emu command on .img files and check for specific log.')
    parser.add_argument('-s', '--source', help='Source folder containing .img files')
    parser.add_argument('-o', '--out', default='./temp/', help='Destination folder for .img files with specific log')
    parser.add_argument('-e', '--emu_dir', default='./rocket-chip/build-32/', help='Directory of emu program (default: Rocket)')
    parser.add_argument('-f', '--seed_file', help='Path to the seed file to be tested')  
    args = parser.parse_args()


    if args.out:
        sys.stdout = Logger("log.txt", path=args.out)
    else:
        sys.stdout = Logger("log.txt") 

    # 0->Rocket 1->NutShell 2->...
    if 'rocket' in args.emu_dir:
        os.environ['SPIKE_HOME'] = './rocket-chip/riscv-isa-sim/'
        benchmark_num = 0
    elif 'NutShell' in args.emu_dir:
        os.environ['SPIKE_HOME'] = './NutShell/riscv-isa-sim'
        benchmark_num = 1
    elif 'XiangShan' in args.emu_dir:
        os.environ['SPIKE_HOME'] = './XiangShan/ready-to-run/'
        os.environ['NOOP_HOME'] = './XiangShan-new/XiangShan/'
        benchmark_num = 2

    if not (args.source or args.seed_file):
        parser.error("Both source folder (-s/--source) and seed file (-sf/--seed_file) must be specified.")


    emu_directory = args.emu_dir  # Directory of the emu program
    assert os.path.exists(emu_directory), f"EMU directory {emu_directory} does not exist."
    if args.source:
        source_folder = args.source  
    dest_folder = args.out 
    emu_directory = args.emu_dir  
    

    os.makedirs(dest_folder, exist_ok=True)

    threads = []  
    futures = []
   
    has_spec_issue = False
    max_threads = 20
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        if benchmark_num == 0:
            if args.seed_file:
                run_command_and_check(args.seed_file, emu_directory, dest_folder)
            else:
                files = [f for f in os.listdir(source_folder) if f.endswith('.img')]
                
                total_files = len(files)
                for filename in files:
                    if filename.endswith('.img'):
                        img_file = os.path.join(source_folder, filename)
                        future = executor.submit(run_command_and_check, img_file, emu_directory, dest_folder)
                        futures.append(future)

        elif benchmark_num == 1:
            if args.seed_file:
                nts_run_command_and_check(args.seed_file, emu_directory, dest_folder)
            else:
                files = [f for f in os.listdir(source_folder) if f.endswith('.img')]
                total_files = len(files)
                for  index, filename in enumerate(files):
                    if filename.endswith('.img'):
                        img_file = os.path.join(source_folder, filename)
                        future = executor.submit(nts_run_command_and_check, img_file, emu_directory, dest_folder)
                        futures.append(future)

        elif benchmark_num == 2:
            if args.seed_file:
                xs_run_command_and_check(args.seed_file, emu_directory, dest_folder)
            else:

                files = [f for f in os.listdir(source_folder) if f.endswith('.img')]
                total_files = len(files)
                for  index, filename in enumerate(files):

                    if filename.endswith('.img'):
                        img_file = os.path.join(source_folder, filename)
                        future = executor.submit(xs_run_command_and_check, img_file, emu_directory, dest_folder)

                        futures.append(future)


        for index, future in enumerate(as_completed(futures), 1):
            show_progress(index, total_files)

    futures = []
    show_progress(0, total_files)
    has_spec_issue = nts_run.get_spec_issue()


    if has_spec_issue  and False: 
        rewrite_asm_files(dest_folder)
        dest_folder_spec = os.path.join(dest_folder,'spec_issue_em')
        rewrite_asm_dir = os.path.join(dest_folder,'spec_issue_em','spec_issue_em_img')

        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            if benchmark_num == 0:
                files = [f for f in os.listdir(rewrite_asm_dir) if f.endswith('.img')]
                total_files = len(files)
                if args.seed_file:
                    run_command_and_check(args.seed_file, emu_directory, dest_folder_spec)
                else:
                    files = [f for f in os.listdir(rewrite_asm_dir) if f.endswith('.img')]#显示
                    total_files = len(files)
                    for filename in files:
                        if filename.endswith('.img'):
                            img_file = os.path.join(rewrite_asm_dir, filename)
                            future = executor.submit(run_command_and_check, img_file, emu_directory, dest_folder_spec)
                            futures.append(future)
            elif benchmark_num == 1:
                files = [f for f in os.listdir(rewrite_asm_dir) if f.endswith('.img')]
                total_files = len(files)
                if args.seed_file:
                    nts_run_command_and_check(args.seed_file, emu_directory, dest_folder_spec)
                else:
                    files = [f for f in os.listdir(rewrite_asm_dir) if f.endswith('.img')]#
                    total_files = len(files)
                    for  index, filename in enumerate(files):
                        if filename.endswith('.img'):
                            img_file = os.path.join(rewrite_asm_dir, filename)
                            future = executor.submit(nts_run_command_and_check, img_file, emu_directory, dest_folder_spec)
                            futures.append(future)
            index = 0
            for index, future in enumerate(as_completed(futures), 1):
                show_progress(index, total_files)




    input_file = dest_folder + '/log.txt'
    output_file = dest_folder + '/log_analyze.txt'
    remove_lines_and_count(input_file,output_file)

if __name__ == "__main__":
    main()
