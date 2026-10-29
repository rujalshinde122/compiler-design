class CodeGenerator:
    def __init__(self, quadruples, symbol_table=None):
        self.quadruples = quadruples
        self.symbol_table = symbol_table or []
        self.assembly_lines = []
        self.machine_code_lines = []
        self.stack_offsets = {}
        self.current_offset = 0

    def _get_operand(self, arg):
        if not arg or arg == "-":
            return "0"
        # Check if number
        if arg.isdigit() or (arg.startswith('-') and arg[1:].isdigit()):
            return arg
        # Variable or temporary in stack
        if arg not in self.stack_offsets:
            self.current_offset += 4
            self.stack_offsets[arg] = self.current_offset
        return f"DWORD PTR [rbp-{self.stack_offsets[arg]}]"

    def _emit_asm(self, line, comment=None):
        if comment:
            formatted = f"    {line:<32} # {comment}"
        elif line.startswith(".") or line.endswith(":"):
            formatted = line
        else:
            formatted = f"    {line}"
        self.assembly_lines.append(formatted)

    def generate(self):
        self.assembly_lines = []
        self.machine_code_lines = []
        self.stack_offsets = {}
        self.current_offset = 0

        # Calculate stack frame requirement
        for q in self.quadruples:
            for item in [q.get("arg1"), q.get("arg2"), q.get("result")]:
                if item and item != "-" and not item.isdigit() and not item.startswith("L_") and not item.startswith("."):
                    if item not in self.stack_offsets:
                        self.current_offset += 4
                        self.stack_offsets[item] = self.current_offset

        # Align stack to 16 bytes
        stack_frame_size = ((self.current_offset + 15) // 16) * 16
        if stack_frame_size == 0:
            stack_frame_size = 16

        # Directives
        self._emit_asm(".intel_syntax noprefix")
        self._emit_asm(".globl main")
        self._emit_asm(".text")
        self._emit_asm("")

        in_function = False

        for q in self.quadruples:
            op = q["op"]
            arg1 = q["arg1"]
            arg2 = q["arg2"]
            res = q["result"]

            if op == "PROC":
                func_name = arg1
                in_function = True
                self._emit_asm(f"{func_name}:")
                self._emit_asm("push rbp", "Save base pointer")
                self._emit_asm("mov rbp, rsp", "Set up stack frame")
                self._emit_asm(f"sub rsp, {stack_frame_size}", f"Allocate {stack_frame_size} bytes stack frame")
                self._emit_asm("")

            elif op == "ENDPROC":
                if in_function:
                    self._emit_asm("mov eax, 0", "Default exit code")
                    self._emit_asm("leave", "Restore stack frame")
                    self._emit_asm("ret", "Return to caller")
                    self._emit_asm("")
                    in_function = False

            elif op == "label":
                label_name = f".{res}" if not res.startswith(".") else res
                self._emit_asm(f"{label_name}:")

            elif op == "goto":
                target = f".{res}" if not res.startswith(".") else res
                self._emit_asm(f"jmp {target}", f"Unconditional jump to {res}")

            elif op == "ifFalse":
                target = f".{res}" if not res.startswith(".") else res
                cond_op = self._get_operand(arg1)
                self._emit_asm(f"cmp {cond_op}, 0", f"Test condition {arg1}")
                self._emit_asm(f"je {target}", f"Branch if false to {res}")

            elif op == "=":
                dest = self._get_operand(res)
                if arg1.isdigit() or (arg1.startswith('-') and arg1[1:].isdigit()):
                    self._emit_asm(f"mov {dest}, {arg1}", f"{res} = {arg1}")
                else:
                    src = self._get_operand(arg1)
                    self._emit_asm(f"mov eax, {src}", f"Load {arg1}")
                    self._emit_asm(f"mov {dest}, eax", f"Store into {res}")

            elif op in ['+', '-', '*', '/', '%']:
                src1 = self._get_operand(arg1)
                src2 = self._get_operand(arg2)
                dest = self._get_operand(res)

                if op == '+':
                    self._emit_asm(f"mov eax, {src1}", f"Load {arg1}")
                    self._emit_asm(f"add eax, {src2}", f"Add {arg2}")
                    self._emit_asm(f"mov {dest}, eax", f"Store result into {res}")
                elif op == '-':
                    self._emit_asm(f"mov eax, {src1}", f"Load {arg1}")
                    self._emit_asm(f"sub eax, {src2}", f"Subtract {arg2}")
                    self._emit_asm(f"mov {dest}, eax", f"Store result into {res}")
                elif op == '*':
                    self._emit_asm(f"mov eax, {src1}", f"Load {arg1}")
                    self._emit_asm(f"imul eax, {src2}", f"Multiply by {arg2}")
                    self._emit_asm(f"mov {dest}, eax", f"Store result into {res}")
                elif op in ['/', '%']:
                    self._emit_asm(f"mov eax, {src1}", f"Load dividend {arg1}")
                    self._emit_asm("cdq", "Sign-extend EAX into EDX:EAX")
                    if arg2.isdigit():
                        self._emit_asm("mov ecx, " + arg2, f"Load divisor {arg2}")
                        self._emit_asm("idiv ecx", "Signed divide")
                    else:
                        self._emit_asm(f"idiv {src2}", f"Signed divide by {arg2}")
                    if op == '/':
                        self._emit_asm(f"mov {dest}, eax", f"Store quotient into {res}")
                    else:
                        self._emit_asm(f"mov {dest}, edx", f"Store remainder into {res}")

            elif op in ['<', '>', '<=', '>=', '==', '!=']:
                src1 = self._get_operand(arg1)
                src2 = self._get_operand(arg2)
                dest = self._get_operand(res)

                self._emit_asm(f"mov eax, {src1}", f"Load {arg1} for comparison")
                if arg2.isdigit():
                    self._emit_asm(f"cmp eax, {arg2}", f"Compare with {arg2}")
                else:
                    self._emit_asm(f"cmp eax, {src2}", f"Compare with {arg2}")

                set_inst = {
                    '<': 'setl',
                    '>': 'setg',
                    '<=': 'setle',
                    '>=': 'setge',
                    '==': 'sete',
                    '!=': 'setne'
                }[op]

                self._emit_asm(f"{set_inst} al", f"Set boolean flag for ({op})")
                self._emit_asm("movzx eax, al", "Zero-extend to 32-bit")
                self._emit_asm(f"mov {dest}, eax", f"Store boolean into {res}")

            elif op == "return":
                if arg1 and arg1 != "-":
                    if arg1.isdigit() or (arg1.startswith('-') and arg1[1:].isdigit()):
                        self._emit_asm(f"mov eax, {arg1}", f"Set return value {arg1}")
                    else:
                        src = self._get_operand(arg1)
                        self._emit_asm(f"mov eax, {src}", f"Load return value {arg1}")
                else:
                    self._emit_asm("mov eax, 0", "Default return 0")
                self._emit_asm("leave", "Restore stack frame")
                self._emit_asm("ret", "Return from function")

            elif op == "DECLARE":
                # Handled via stack allocation
                pass

        # If file had no procedure wrapper, synthesize main
        if not in_function and len(self.quadruples) > 0 and not any(q['op'] == 'PROC' for q in self.quadruples):
            pass

        # Generate simulated Machine Bytecode
        self._generate_machine_bytecode(stack_frame_size)

        assembly_text = "\n".join(self.assembly_lines)
        return assembly_text, self.assembly_lines, self.machine_code_lines

    def _generate_machine_bytecode(self, frame_size):
        """
        Translates assembly instructions into representative x86-64 machine language hex byte sequences.
        """
        addr = 0x1000
        self.machine_code_lines = []

        def add_code(hex_bytes, instruction, desc=""):
            nonlocal addr
            byte_str = " ".join([f"{b:02X}" for b in hex_bytes])
            self.machine_code_lines.append({
                "address": f"0x{addr:08X}",
                "bytes": byte_str,
                "assembly": instruction,
                "description": desc
            })
            addr += len(hex_bytes)

        # Standard prologue
        add_code([0x55], "push rbp", "Push base pointer onto stack")
        add_code([0x48, 0x89, 0xE5], "mov rbp, rsp", "Copy stack pointer to base pointer")
        add_code([0x48, 0x83, 0xEC, frame_size & 0xFF], f"sub rsp, 0x{frame_size:02X}", "Reserve stack space")

        for q in self.quadruples:
            op = q["op"]
            arg1 = q["arg1"]
            arg2 = q["arg2"]
            res = q["result"]

            if op == "=":
                if arg1.isdigit():
                    val = int(arg1) & 0xFFFFFFFF
                    bytes_val = [(val >> (i * 8)) & 0xFF for i in range(4)]
                    offset = self.stack_offsets.get(res, 4)
                    add_code([0xC7, 0x45, 0x100 - offset] + bytes_val, f"mov DWORD PTR [rbp-{offset}], {arg1}", f"Store {arg1} in {res}")
                else:
                    offset = self.stack_offsets.get(res, 4)
                    add_code([0x89, 0x45, 0x100 - offset], f"mov DWORD PTR [rbp-{offset}], eax", f"Store EAX in {res}")
            elif op == "+":
                add_code([0x03, 0x45, 0xF8], f"add eax, [rbp-offset]", f"Integer addition: {arg1} + {arg2}")
            elif op == "-":
                add_code([0x2B, 0x45, 0xF8], f"sub eax, [rbp-offset]", f"Integer subtraction: {arg1} - {arg2}")
            elif op == "*":
                add_code([0x0F, 0xAF, 0x45, 0xF8], f"imul eax, [rbp-offset]", f"Signed integer multiply")
            elif op == "return":
                val = int(arg1) if arg1.isdigit() else 0
                bytes_val = [(val >> (i * 8)) & 0xFF for i in range(4)]
                add_code([0xB8] + bytes_val, f"mov eax, {val}", f"Load return code {val}")
                add_code([0xC9], "leave", "High level procedure exit")
                add_code([0xC3], "ret", "Near return to caller")

        if not any(q['op'] == 'return' for q in self.quadruples):
            add_code([0xB8, 0x00, 0x00, 0x00, 0x00], "mov eax, 0", "Exit code 0")
            add_code([0xC9], "leave", "High level procedure exit")
            add_code([0xC3], "ret", "Near return to caller")

def generate_target_code(quadruples, symbol_table=None):
    generator = CodeGenerator(quadruples, symbol_table)
    asm_text, asm_lines, machine_code = generator.generate()
    return asm_text, asm_lines, machine_code
