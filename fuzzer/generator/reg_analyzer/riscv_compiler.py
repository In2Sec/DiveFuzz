"""
RISC-V 指令编译器包装器
使用 riscv-gnu-toolchain 编译单条指令为机器码
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


class RiscvCompiler:
    """使用 riscv-gnu-toolchain 编译 RISC-V 指令"""

    def __init__(
        self,
        as_cmd: str = "riscv64-unknown-elf-as",
        objcopy_cmd: str = "riscv64-unknown-elf-objcopy",
        default_march: str = "rv64imafdcv_zicsr_zifencei_zba_zbb_zbc_zbs_zfh"
    ):
        """
        初始化编译器

        Args:
            as_cmd: 汇编器命令
            objcopy_cmd: objcopy 命令
            default_march: 默认架构字符串（支持尽可能多的扩展）
        """
        self.as_cmd = as_cmd
        self.objcopy_cmd = objcopy_cmd
        self.default_march = default_march

        # 验证工具链是否可用
        self._verify_toolchain()

    def _verify_toolchain(self):
        """验证 RISC-V 工具链是否可用"""
        try:
            result = subprocess.run(
                [self.as_cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                raise RuntimeError(f"Assembler verification failed: {result.stderr}")
        except FileNotFoundError:
            raise RuntimeError(
                f"RISC-V toolchain not found: {self.as_cmd}\n"
                f"Please install riscv-gnu-toolchain and ensure it's in PATH"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Assembler verification timed out")

    def compile_instruction(
        self,
        asm_instruction: str,
        march: Optional[str] = None
    ) -> int:
        """
        编译单条汇编指令为机器码

        Args:
            asm_instruction: 汇编指令字符串（如 "add x1, x2, x3"）
            march: 可选的架构字符串，如果不指定则使用 default_march

        Returns:
            32 位机器码（整数）

        Raises:
            RuntimeError: 如果编译失败
        """
        if march is None:
            march = self.default_march

        with tempfile.TemporaryDirectory() as tmpdir:
            asm_file = Path(tmpdir) / "inst.s"
            obj_file = Path(tmpdir) / "inst.o"
            bin_file = Path(tmpdir) / "inst.bin"

            # 写入汇编文件
            with open(asm_file, 'w') as f:
                f.write(".text\n")
                f.write(f"    {asm_instruction}\n")

            # 汇编
            as_result = subprocess.run(
                [self.as_cmd, f"-march={march}", "-o", str(obj_file), str(asm_file)],
                capture_output=True,
                text=True,
                timeout=10
            )

            if as_result.returncode != 0:
                # 尝试提取更有用的错误信息
                error_msg = as_result.stderr.strip()
                raise RuntimeError(
                    f"Failed to assemble instruction: '{asm_instruction}'\n"
                    f"Architecture: {march}\n"
                    f"Error: {error_msg}"
                )

            # 提取二进制
            objcopy_result = subprocess.run(
                [self.objcopy_cmd, "-O", "binary", str(obj_file), str(bin_file)],
                capture_output=True,
                text=True,
                timeout=10
            )

            if objcopy_result.returncode != 0:
                raise RuntimeError(
                    f"Failed to extract binary from object file\n"
                    f"Error: {objcopy_result.stderr}"
                )

            # 读取机器码
            with open(bin_file, 'rb') as f:
                machine_code_bytes = f.read()

            if len(machine_code_bytes) == 0:
                raise RuntimeError(
                    f"Invalid machine code length: 0 bytes\n"
                    f"Failed to generate machine code for instruction"
                )

            # 处理压缩指令（2字节）和标准指令（4字节）
            if len(machine_code_bytes) == 2:
                # 压缩指令（C扩展）：零填充为4字节
                # Spike会正确执行2字节指令，忽略后面的0填充
                machine_code_bytes = machine_code_bytes + b'\x00\x00'
            elif len(machine_code_bytes) < 2:
                raise RuntimeError(
                    f"Invalid machine code length: {len(machine_code_bytes)} bytes\n"
                    f"Expected at least 2 bytes for a RISC-V instruction"
                )

            # 转换为整数（小端序），使用前4字节
            machine_code = int.from_bytes(machine_code_bytes[:4], byteorder='little')

            return machine_code

    def compile_multiple(
        self,
        instructions: list[str],
        march: Optional[str] = None
    ) -> list[int]:
        """
        批量编译多条指令

        Args:
            instructions: 指令列表
            march: 可选的架构字符串

        Returns:
            机器码列表
        """
        results = []
        for instruction in instructions:
            machine_code = self.compile_instruction(instruction, march)
            results.append(machine_code)
        return results


# 便捷函数
def compile_instruction(
    instruction: str,
    march: str = "rv64imafdcv_zicsr_zifencei_zba_zbb_zbc_zbs_zfh"
) -> int:
    """
    便捷函数：编译单条指令

    Args:
        instruction: 汇编指令
        march: 架构字符串

    Returns:
        机器码
    """
    compiler = RiscvCompiler(default_march=march)
    return compiler.compile_instruction(instruction)


if __name__ == "__main__":
    # 测试编译器
    compiler = RiscvCompiler()

    test_instructions = [
        "add x1, x2, x3",
        "addi x1, x2, 100",
        "lui x1, 0x12345",
    ]

    print("Testing RISC-V compiler...")
    for instruction in test_instructions:
        try:
            machine_code = compiler.compile_instruction(instruction)
            print(f"✓ {instruction:30s} -> 0x{machine_code:08x}")
        except Exception as e:
            print(f"✗ {instruction:30s} -> Error: {e}")
