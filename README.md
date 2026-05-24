# Auto CTF Solver

Automated CTF challenge solving with multi-agent architecture. Triages challenges into categories, dispatches to specialist agents, and generates writeup documents with screenshots.

## Architecture

```
Challenge → Triage Agent → Specialist Agent → Writeup Generator
                │                │                   │
         (identify type)   (PWN/Web/Rev/        (.docx + .md)
                           Crypto/MISC/Mobile)
```

**Multi-agent system:**
- **Triage Agent** — analyzes files/descriptions to identify challenge category
- **PWN Agent** — binary exploitation (BOF, ROP, heap, format string, seccomp)
- **Web Agent** — web exploitation (SSTI, SQLi, SSRF, JWT, deserialization)
- **Reverse Agent** — reverse engineering (PE/ELF, Android APK, .so analysis)
- **Crypto Agent** — cryptography (RSA, AES modes, PRNG, lattice, custom hash)
- **MISC Agent** — steganography, forensics, jail escape, encodings
- **Mobile Agent** — Android APK, native .so, Frida hooks

**Writeup generator:** produces `.docx` (Word) with embedded screenshots and `.md` (Markdown) for CTFtime/GitHub.

## Quick Start

```bash
# Install
pip install -e .

# Solve a challenge (auto-detect category)
ctf-solve solve -f challenge.zip -d "Find the hidden flag"

# Solve with explicit category
ctf-solve solve -f chall.elf -c pwn --host 10.0.0.1 --port 1337

# Solve and generate writeup
ctf-solve solve -f challenge.png -w

# Watch directory for new challenges
ctf-watch D:/CTF/exam/agent2 --writeup

# Generate writeup from existing solve log
ctf-writeup solve_log.json -n "My Challenge" -c web
```

## Configuration

Set environment variables or create `.env`:

```bash
ANTHROPIC_API_KEY=sk-ant-...    # Required: Anthropic API key
ANTHROPIC_MODEL=claude-sonnet-4-6  # Model to use
CTF_DOCKER_CONTAINER=ctf-tools-agent2  # Docker container for tool execution
CTF_WORK_DIR=D:/CTF/exam/agent2  # Working directory
CTF_WRITEUP_FORMATS=docx,md      # Output formats
```

## Project Structure

```
src/auto_ctf/
├── agents/
│   ├── base.py          # Base agent + data classes
│   ├── triage.py        # Challenge type identification
│   ├── specialists.py   # PWN/Web/Reverse/Crypto/MISC/Mobile agents
│   └── dispatcher.py    # Routes challenges to specialists
├── writeup/
│   ├── generator.py     # Writeup orchestrator
│   ├── docx_writer.py   # Word .docx generation
│   └── md_writer.py     # Markdown generation
├── tools/
│   ├── docker.py        # Docker container management
│   ├── screenshot.py    # Screenshot capture (scrot/CutyCapt)
│   └── common.py        # File analysis utilities
├── knowledge/
│   └── patterns.py      # Learned solve patterns per category
├── config/
│   └── settings.py      # Central configuration
├── cli.py               # CLI entry point
└── watcher.py           # Directory watcher
```

## Features

- **Auto-triage**: detects challenge type from files, magic bytes, and keywords
- **Knowledge-driven**: 50+ learned solve patterns across 6 categories
- **Docker isolation**: all tool execution happens in isolated containers
- **Rate-limit compliant**: enforces safe scanning parameters (nmap -T2, sqlmap --delay=1)
- **Screenshot capture**: automatic terminal/web screenshots for writeups
- **Dual writeup format**: generates both `.docx` (with embedded images) and `.md`

## Token 消耗与额度需求

本项目基于多智能体架构，实测单日 Token 消耗已突破 **1 亿（100M）**，主要来自多 Agent 多轮长上下文协同调用。

| 指标 | 数值 |
|---|---|
| 单次解题 Token | ~40,000 |
| **单日峰值 Token** | **~100,000,000（1 亿）** |
| 月均消耗 | **~2.5-3 亿** |
| **年化需求** | **远超 10 亿（30 亿+）** |

> 消耗瓶颈在于多轮上下文累积（占比 74%）——每次交互携带完整历史，输入 Token 随轮次线性增长。

详细分析见 **[docs/TOKEN_USAGE_ANALYSIS.md](docs/TOKEN_USAGE_ANALYSIS.md)**。

## Requirements

- Python 3.10+
- Docker (with ctf-tools container)
- Anthropic API key (Tier 2+ recommended for sustained use)

## License

MIT
