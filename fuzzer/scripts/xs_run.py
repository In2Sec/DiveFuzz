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
from check_xor import check_xor_and_execute
from generater.spec_em_nts import save_issue_asm# TODO

has_spec_issue=False

def xs_run_command_and_check(img_file, emu_directory, dest_folder):

    command = f"{emu_directory}/emu -b 0 -e 0 -i {img_file} --diff ./XiangShan/ready-to-run/riscv64-spike-so"

    

    img_file_name = os.path.basename(img_file)
    timeout = 1200 
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
        print(f"Timeout! Copied {img_file} to {abd_dir_path}")
        return  


    failed_dir_name = "failed_finished" 
    failed_dir_path = os.path.join(dest_folder, failed_dir_name)
    os.makedirs(failed_dir_path, exist_ok=True)

    strange_dir_name = "strange_finished" 
    strange_dir_path = os.path.join(dest_folder, strange_dir_name)
    os.makedirs(strange_dir_path, exist_ok=True)


    positive_bug_path = "positive_bug" 
    positive_bug_dir_path = os.path.join(dest_folder, positive_bug_path)
    os.makedirs(positive_bug_dir_path, exist_ok=True)


    global has_spec_issue
    prev_line = ''
    spec_tag = 0
    recent_lines = []  
    last_commit_instr = 0 


    different_count = 0
    bug_flag = True
    first_diff = False
    success_end = False
    wfi_is_31 = False 
    bug_number = 0 
    cascade_succ_tag = False
    kmh_success_end = False

    for line in stdout.decode().split('\n') + stderr.decode().split('\n'):

        recent_lines.append(line) 

        img_file_name = os.path.basename(img_file)
        if len(recent_lines) > 32:
            recent_lines.pop(0)
        
        if 'different at pc' in line  and spec_tag == 0 or 'Mismatch' in line:
            if kmh_success_end:
                continue
            if not first_diff:
                print(f"\033[91mBug report:\033[0m","\t",img_file_name)
                first_diff = True
                bug_flag = False
            different_count += 1
            print(f"\033[91m\t{line}\033[0m")  
        elif 'different at pc' in line:
            different_count += 1  
        if 'instrCnt =' in line:
            instrCnt_value = line.split('=')[1].strip()
            if first_diff:
                print(f"\tinstrCnt value: {instrCnt_value}")
        if 'wfi <--' in line:
            success_end = True
    

        # The purpose of the WFI instruction is to provide a hint to the implementation, 
        # and so a legal implementation is to simply implement WFI as a NOP.
        # if 'wfi' in prev_line and ('auipc' in line and 't5' in line and '0x3' in line and '<--' in line):
        if 'wfi' in prev_line and ('auipc' in line and 't5' in line \
                                            and '<--' in line):
            last_commit_instr = 1
            print(f"\033[93mThis is spec issue 1: wfi as nop \033[0m")
            spec_tag = 1
            success_end = True
            print("\033[32m\tBut Successfully Finished! Not Save The File!\033[0m")


        if 'csrw' in line and 'mtvec' in line and '<--' in line:
            last_commit_instr = 2
            spec_tag = 2
            success_end = True

        if 'wfi' in recent_lines[-1] and ('auipc' in recent_lines[0] \
                        and 't5' in recent_lines[0]  and '<--' in recent_lines[0]):
            last_commit_instr = 3
            print(f"\033[93mThis is spec issue 3: wfi as nop \033[0m")
            spec_tag = 3
            success_end = True
            print("\033[32m\tBut Successfully Finished! Not Save The File!\033[0m")
        if 'csrw' in line and 'stvec' in line and '<--' in line:
            last_commit_instr = 4
            spec_tag = 4
            success_end = True 


        if 'wfi' in prev_line and ('li' in line and 'ra' in line and '39' in line\
                                            and '<--' in line):
            last_commit_instr = 1
            print(f"\033[93mThis is spec issue 1: wfi as nop \033[0m")

            spec_tag = 1

            success_end = True
            print("\033[32m\tBut Successfully Finished! Not Save The File!\033[0m")
        if 'wfi' in recent_lines[-1] and ('li' in recent_lines[0] and '39' in line\
                        and 'ra' in recent_lines[0]  and '<--' in recent_lines[0]):
            last_commit_instr = 3
            print(f"\033[93mThis is spec issue 3: wfi as nop \033[0m")
            spec_tag = 1
            success_end = True
            print("\033[32m\tBut Successfully Finished! Not Save The File!\033[0m")

        if 'wfi' in recent_lines[-1] and ('li' in recent_lines[0] and '39' in line\
                        and 'ra' in recent_lines[0]  and '<--' in recent_lines[0]):
            last_commit_instr = 3
            print(f"\033[93mThis is spec issue 3: wfi as nop \033[0m")
            spec_tag = 1
            success_end = True
            print("\033[32m\tBut Successfully Finished! Not Save The File!\033[0m")

        if 'li' in line and '39' in line\
                        and 'ra' in line  and '<--' in line\
                        and '[00]' in line:
            wfi_is_31 = True

        if wfi_is_31 and ('wfi' in line and '[31]' in line):
            last_commit_instr = 3
            print(f"\033[93mThis is spec issue 4: wfi as nop finally \033[0m")
            spec_tag = 1
            success_end = True
            print("\033[32m\tBut Successfully Finished! Not Save The File!\033[0m")

        ######################################################################## For fuzz KUNMINGHU #############################################################################################

        if 'No instruction of core 0 commits for 15000 cycles, maybe get stuck':
            cascade_succ_tag = True

        if 'HIT GOOD TRAP' in line:
            success_end = True
            kmh_success_end = True



        prev_line = line


    if spec_tag == 0:

        if  bug_flag:
            print(f"PASSED!{img_file}")
            print(f"\tinstrCnt value: {instrCnt_value}")

        if success_end and kmh_success_end:
            print("\033[32m\tSuccessfully Finished!(GOOD TRAP)\033[0m")
        elif success_end:
            print("\033[32m\tSuccessfully Finished!\033[0m")
        else:
            if different_count == 0 and cascade_succ_tag:
                print(f"\033[32m\tCascade's seed successfully end!\n\033[0m")

            elif different_count == 0:
                print(f"\033[91m\tStrange end!\n\033[0m")
                shutil.copy(img_file, strange_dir_path)
            else:
                print(f"\033[91m\tFaild Finished!\n\033[0m")
                shutil.copy(img_file, failed_dir_path)

        if success_end and not bug_flag:
            shutil.copy(img_file, positive_bug_dir_path)
    elif spec_tag == 1:
        print(f"\tinstrCnt value: {instrCnt_value}")
        spec_issue_1_name = "spec_issue_1_name"
        spec_issue_1_dir_path = os.path.join(dest_folder, spec_issue_1_name)
        os.makedirs(spec_issue_1_dir_path, exist_ok=True)


    elif spec_tag == 2:
        print(f"\tinstrCnt value: {instrCnt_value}")
        if different_count == 1 and check_xor_and_execute(recent_lines) == 1:
            print(f"\033[93mThis is spec issue 2: mtvec's MODE is diff \033[0m")
            print("\033[32m\tBut Successfully Finished!\033[0m")
            spec_issue_2_name = "spec_issue_2_name"
            spec_issue_2_dir_path = os.path.join(dest_folder, spec_issue_2_name)
            os.makedirs(spec_issue_2_dir_path, exist_ok=True)
            shutil.copy(img_file, spec_issue_2_dir_path)
            img_file_name = os.path.basename(img_file)

            new_img_path = os.path.abspath(os.path.join(spec_issue_2_dir_path, img_file_name))

            has_spec_issue = True
            save_issue_asm(new_img_path,spec_tag)

    elif spec_tag == 3:
        print(f"\tinstrCnt value: {instrCnt_value}")
        spec_issue_3_name = "spec_issue_3_name"
        spec_issue_3_dir_path = os.path.join(dest_folder, spec_issue_3_name)
        os.makedirs(spec_issue_3_dir_path, exist_ok=True)
    elif spec_tag == 4:
        print(f"\tinstrCnt value: {instrCnt_value}")
        if different_count == 1 and check_xor_and_execute(recent_lines) == 1:
            print(f"\033[93mThis is spec issue 4: stvec's MODE is diff \033[0m")
            print("\033[32m\tBut Successfully Finished!\033[0m")
            spec_issue_4_name = "spec_issue_4_name"
            spec_issue_4_dir_path = os.path.join(dest_folder, spec_issue_4_name)
            os.makedirs(spec_issue_4_dir_path, exist_ok=True)
            shutil.copy(img_file, spec_issue_4_dir_path)

            img_file_name = os.path.basename(img_file)

            new_img_path = os.path.abspath(os.path.join(spec_issue_4_dir_path, img_file_name))

            has_spec_issue = True
            save_issue_asm(new_img_path,spec_tag)
        else:
            print(f"\033[95m\tNOT SURE!\033[0m")
            not_sure = "not_sure"
            not_sure_dir_path = os.path.join(dest_folder, not_sure)
            os.makedirs(not_sure_dir_path, exist_ok=True)
            shutil.copy(img_file, not_sure_dir_path)


def get_spec_issue():
    """
    Return the value of the global variable.
    """
    return has_spec_issue
