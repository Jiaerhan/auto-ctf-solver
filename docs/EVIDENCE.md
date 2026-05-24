# Project Usage Evidence — Auto CTF Solver

## 1. Project Information

| Field | Value |
|---|---|
| **Project Name** | auto-ctf-solver |
| **Repository** | https://github.com/Jiaerhan/auto-ctf-solver |
| **Language** | Python 3.10+ |
| **Tech Stack** | Anthropic SDK (Claude Sonnet 4.6), Docker, python-docx, pytest |
| **Architecture** | Multi-Agent (Triage + 6 Specialist Agents + Writeup Generator) |
| **License** | MIT (Open Source) |

## 2. Measured Token Consumption

During recent high-intensity CTF training (2026-05), the project sustained the following consumption profile:

| Metric | Value |
|---|---|
| **Single-day Peak** | **~100,000,000 tokens (100M)** |
| **Daily Full-pipeline Runs** | 5-10 sessions |
| **Challenges per Session** | 3-8 challenges (mixed categories) |
| **Monthly Average** | **~250-300M tokens** |
| **Annual Projection** | **3B+ tokens** |

### Daily Breakdown (Typical High-Intensity Day)

| Time Window | Activity | Agent Calls | Est. Tokens |
|---|---|---|---|
| 09:00-12:00 | PWN training (5 challenges) | PwnAgent × 5, avg 6 rounds each | ~35M |
| 13:00-16:00 | Web + Reverse (6 challenges) | WebAgent × 3 + RevAgent × 3 | ~28M |
| 16:00-18:00 | MISC + Crypto (4 challenges) | MiscAgent × 3 + CryptoAgent × 1 | ~15M |
| 19:00-22:00 | Review + Writeup generation | All agents writeup generation | ~22M |
| **Total** | **15 challenges + 15 writeups** | **6 agent types across all sessions** | **~100M** |

## 3. Multi-Agent Collaborative Workflow

```
Challenge Input
      │
      ▼
┌──────────────┐
│ Triage Agent │  ← Local rules engine, 0 LLM tokens
│  (category)  │     File type + keywords + magic bytes
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ Specialist Agent │  ← Category-specific solve patterns injected
│  (PWN/Web/Rev/  │     Knowledge base: 50+ patterns across 6 categories
│   Crypto/MISC/   │     Long-context multi-turn dialogue with Claude
│   Mobile)        │     3-12+ rounds depending on difficulty
└──────┬───────────┘
       │  (per round: tool output injected into context)
       │  (context accumulates linearly: bottleneck at ~74% of total spend)
       ▼
┌──────────────┐
│  Multi-turn  │  ← Round N input = base_prompt + Σ(round 1..N-1 outputs + tool results)
│  Interaction │     Complex challenges (heap, seccomp): 6-8 rounds, ~120K tokens
│  with Claude │     Extreme challenges (kernel, VM escape): 12+ rounds, ~250K+ tokens
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ Writeup Generator│  ← Dual output: .docx (with embedded screenshots) + .md
│  (.docx + .md)   │     7-section template: Info → Approach → Analysis → Exploit → Flag → Lessons
└──────────────────┘
```

### Why Token Consumption is High

1. **Multi-Agent Concurrency**: 6 specialist agents each maintain independent long-context sessions
2. **Context Accumulation**: Every round carries full conversation history (system prompt + all prior rounds + all tool outputs), growing linearly: `input_N ≈ base + (N-1) × 2,300 tokens`
3. **Tool Output Injection**: ROPgadget output (3K-5K tokens), objdump disassembly, strings output — all enter the context window
4. **Writeup Generation**: Each solved challenge produces both .docx and .md writeups with full 7-section content
5. **Scale, Not Unit Cost**: Single-challenge efficiency (~40K tokens) is proven; the bottleneck is the volume and concurrency of multi-agent collaboration

## 4. Application Justification

> **This project requires Anthropic Tier 4+ API access with a minimum monthly quota of 500M tokens.** The measured daily peak of 100M tokens, monthly average of 250-300M tokens, and annualized projection exceeding 3 billion tokens far surpass standard tier limits. The multi-agent architecture inherently demands high-concurrency long-context calls across 6 specialist agents, making elevated rate limits essential for sustained operation.

## 5. Supporting Materials

- [TOKEN_USAGE_ANALYSIS.md](TOKEN_USAGE_ANALYSIS.md) — Detailed per-stage token breakdown and bottleneck analysis
- [SOLVE_DEMO.md](SOLVE_DEMO.md) — Full PWN challenge solve demo log (3 rounds, ~40K tokens)
- [terminal_log.txt](terminal_log.txt) — Live terminal output from `ctf-solve solve` demonstration
