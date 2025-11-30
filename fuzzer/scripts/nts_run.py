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
import re
from check_xor import check_xor_and_execute, check_diff_csr
from generater.spec_em_nts import save_issue_asm
from bug_fliter_nts import fliter_known_bug


has_spec_issue=False

def nts_run_command_and_check(img_file, emu_directory, dest_folder):

    command = f"{emu_directory}/emu -b 0 -e 0 -i {img_file} --diff ./NutShell/ready-to-run/riscv64-nemu-interpreter-so"

    img_file_name = os.path.basename(img_file)

    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    failed_dir_name = "failed_finished" 
    failed_dir_path = os.path.join(dest_folder, failed_dir_name)
    os.makedirs(failed_dir_path, exist_ok=True)


    strange_dir_name = "strange_end_position" 
    strange_dir_path = os.path.join(dest_folder, strange_dir_name)
    os.makedirs(strange_dir_path, exist_ok=True)


    positive_bug_path = "positive_bug" 
    positive_bug_dir_path = os.path.join(dest_folder, positive_bug_path)
    os.makedirs(positive_bug_dir_path, exist_ok=True)

    global has_spec_issue
    different_count = 0
    bug_flag = True
    first_diff = False
    success_end = False
    prev_line = ''
    spec_tag = 0
    bug_number = 0 
    recent_lines = []  
    last_commit_instr = 0 
    for line in stdout.decode().split('\n') + stderr.decode().split('\n'):

        recent_lines.append(line) 
        if len(recent_lines) > 32:
            recent_lines.pop(0)
        
        if 'different at pc' in line and spec_tag == 0 or 'Mismatch' in line:
            if not first_diff:
                print(f"\033[91mBug report:\033[0m",img_file_name)
                first_diff = True
                bug_flag = False
            different_count += 1   # TODO: Later, scheduling can be done based on the number of diffs, or prioritizing one of the new metrics.
            print(f"\033[91m\t{line}\033[0m")  #
        elif 'different at pc' in line:
            different_count += 1  
        if 'instrCnt =' in line:
            instrCnt_value = line.split('=')[1].strip()
            if first_diff:
                print(f"\tinstrCnt value: {instrCnt_value}")
        if 'wfi <--' in line:
            success_end = True
            print("1\n")
        if 'wfi' in prev_line and ('auipc' in line and 't5' in line  and '<--' in line):
            last_commit_instr = 1
            print(f"\033[93mThis is spec issue 1: wfi as nop \n\033[0m")
            spec_tag = 1
            success_end = True
            print("\033[32m\tBut Successfully Finished! Not Save The File!\n\033[0m")


        if 'csrw' in line and 'mtvec' in line and '<--' in line:
            last_commit_instr = 2
            spec_tag = 2
            success_end = True

        if 'wfi' in recent_lines[-1] and ('auipc' in recent_lines[0] \
                        and 't5' in recent_lines[0]  and '<--' in recent_lines[0]):
            last_commit_instr = 3
            print(f"\033[93mThis is spec issue 3: wfi as nop \n\033[0m")
            spec_tag = 3
            success_end = True
            print("\033[32m\tBut Successfully Finished! Not Save The File!\n\033[0m")

        if 'csrw' in line and 'stvec' in line and '<--' in line:
            last_commit_instr = 4
            spec_tag = 4
       
            success_end = True 
        
        if (('<--' in line and 'mret' in prev_line) or ('mret' in recent_lines[-1]\
                                    and '<--' in recent_lines[0])): 
            print(f"\033[93mThis is spec issue 5 \n\033[0m")
            spec_tag = 5
            success_end = True 
       
        if 'wfi' in prev_line and ('li' in line and 'ra' in line  and '39' in line and '<--' in line):
            last_commit_instr = 6
            print(f"\033[93mThis is spec issue 6: wfi as nop \n\033[0m")
            spec_tag = 1 
            success_end = True
            print("\033[32m\tBut Successfully Finished! Not Save The File!\n\033[0m")
        if 'wfi' in recent_lines[-1] and ('li' in recent_lines[0] and '39' in line\
                        and 'ra' in recent_lines[0]  and '<--' in recent_lines[0]):
            last_commit_instr = 3
            print(f"\033[93mThis is spec issue 3: wfi as nop \033[0m")
            spec_tag = 1
            success_end = True
            print("\033[32m\tBut Successfully Finished! Not Save The File!\033[0m")
        
        if '<--' in line:
            bug_number = fliter_known_bug(line)

        prev_line = line


    if spec_tag == 0:
        if  bug_flag:
            print(f"PASSED!{img_file}\n")
            print(f"\tinstrCnt value: {instrCnt_value}\n")
      
        if success_end:
            print("\033[32m\tSuccessfully Finished!\n\033[0m")
        else:
            
            if different_count == 0:
                print(f"\033[91m\tStrange end!\n\033[0m")
                shutil.copy(img_file, strange_dir_path)
            else:
                print(f"\033[91m\tFaild Finished!\n\033[0m")
                shutil.copy(img_file, failed_dir_path)

        if success_end and not bug_flag:
            shutil.copy(img_file, positive_bug_dir_path)

    elif spec_tag == 1:
        print(f"\tinstrCnt value: {instrCnt_value}\n") 
        spec_issue_1_name = "spec_issue_1_name"
        spec_issue_1_dir_path = os.path.join(dest_folder, spec_issue_1_name)
        os.makedirs(spec_issue_1_dir_path, exist_ok=True)

    elif spec_tag == 2:
        print(f"\tinstrCnt value: {instrCnt_value}")
        if different_count == 1 and check_xor_and_execute(recent_lines) == 1:
            print(f"\033[93mThis is spec issue 2: mtvec's MODE is diff \n\033[0m")
            print("\033[32m\tBut Successfully Finished!\n\033[0m")
            spec_issue_2_name = "spec_issue_2_name"
            spec_issue_2_dir_path = os.path.join(dest_folder, spec_issue_2_name)
            os.makedirs(spec_issue_2_dir_path, exist_ok=True)
            shutil.copy(img_file, spec_issue_2_dir_path)

            img_file_name = os.path.basename(img_file)

            new_img_path = os.path.abspath(os.path.join(spec_issue_2_dir_path, img_file_name))

            has_spec_issue = True
            save_issue_asm(new_img_path,spec_tag)


        else:
            print(f"\033[95m\tNOT SURE!\n\033[0m")
            not_sure = "not_sure"
            not_sure_dir_path = os.path.join(dest_folder, not_sure)
            os.makedirs(not_sure_dir_path, exist_ok=True)
            shutil.copy(img_file, not_sure_dir_path)
    
    elif spec_tag == 3:
        print(f"\tinstrCnt value: {instrCnt_value}")
        spec_issue_3_name = "spec_issue_3_name"
        spec_issue_3_dir_path = os.path.join(dest_folder, spec_issue_3_name)
        os.makedirs(spec_issue_3_dir_path, exist_ok=True)
    elif spec_tag == 4:
        print(f"\tinstrCnt value: {instrCnt_value}")
        if different_count == 1 and check_xor_and_execute(recent_lines) == 1:
            print(f"\033[93mThis is spec issue 4: stvec's MODE is diff \n\033[0m")
            print("\033[32m\tBut Successfully Finished!\n\033[0m")
            spec_issue_4_name = "spec_issue_4_name"
            spec_issue_4_dir_path = os.path.join(dest_folder, spec_issue_4_name)
            os.makedirs(spec_issue_4_dir_path, exist_ok=True)
            shutil.copy(img_file, spec_issue_4_dir_path)

            img_file_name = os.path.basename(img_file)

            new_img_path = os.path.abspath(os.path.join(spec_issue_4_dir_path, img_file_name))

            has_spec_issue = True
            save_issue_asm(new_img_path,spec_tag)
        else:
            print(f"\033[95m\tNOT SURE!\n\033[0m")
            not_sure = "not_sure"
            not_sure_dir_path = os.path.join(dest_folder, not_sure)
            os.makedirs(not_sure_dir_path, exist_ok=True)
            shutil.copy(img_file, not_sure_dir_path)
    elif spec_tag == 5:
        if different_count == 4 and check_diff_csr:
            print(f"\033[93mThis is spec issue 5: nts's adress will add 0x80000000 \n\033[0m")
            print("\033[32m\tBut Successfully Finished!\n\033[0m")
            spec_issue_5_name = "spec_issue_5_name"
            spec_issue_5_dir_path = os.path.join(dest_folder, spec_issue_5_name)
            os.makedirs(spec_issue_5_dir_path, exist_ok=True)
            shutil.copy(img_file, spec_issue_5_dir_path)

            img_file_name = os.path.basename(img_file)

            new_img_path = os.path.abspath(os.path.join(spec_issue_5_dir_path, img_file_name))

            has_spec_issue = True
            save_issue_asm(new_img_path, spec_tag)
        else:
            print(f"\033[95m\tNOT SURE!\n\033[0m")
            not_sure = "not_sure"
            not_sure_dir_path = os.path.join(dest_folder, not_sure)
            os.makedirs(not_sure_dir_path, exist_ok=True)
            shutil.copy(img_file, not_sure_dir_path)

def get_spec_issue():
    """
    Return the value of the global variable.
    """
    return has_spec_issue
