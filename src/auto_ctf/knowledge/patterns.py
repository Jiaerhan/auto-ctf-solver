"""Knowledge base: learned CTF solve patterns, tactics, and heuristics.

This module encodes all the patterns discovered from solving hundreds of CTF challenges.
Each category has its own pattern dictionary that drives the specialist agent's approach.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Priority(str, Enum):
    FIRST = "first"        # Try before anything else
    HIGH = "high"          # Very likely approach
    MEDIUM = "medium"      # Common approach
    LOW = "low"            # Edge case
    LAST_RESORT = "last"   # Only after exhausting everything else


@dataclass
class TriageRule:
    """A rule for identifying a challenge's category."""
    category: str
    indicators: list[str]       # File extensions, magic bytes, URL patterns
    keywords: list[str]         # Keywords in challenge description
    weight: float = 1.0         # Confidence weight


@dataclass
class SolvePattern:
    """A known solve pattern for a specific category."""
    name: str
    description: str
    priority: Priority
    tools: list[str]            # Tools needed
    prompt_hint: str            # Hint for the Claude agent
    example_indicators: list[str] = field(default_factory=list)


# ─── Triage Rules ────────────────────────────────────────────────

TRIAGE_RULES: list[TriageRule] = [
    # PWN
    TriageRule("pwn", ["elf", "x86", "x64", "arm", "mips"], ["bof", "overflow", "shell", "rop", "heap", "format string", "bin", "executable"], 1.0),
    TriageRule("pwn", ["amd64", "i386"], ["stack", "buffer", "libc", "got", "plt", "canary", "nx", "pie", "aslr"], 1.0),

    # Web
    TriageRule("web", ["html", "js", "php", "asp", "jsp"], ["xss", "sqli", "ssti", "ssrf", "xxe", "csrf", "rce", "lfi", "rfi", "idor", "upload"], 1.0),
    TriageRule("web", [".php", ".asp", ".jsp", ".war"], ["web", "http", "url", "cookie", "session", "jwt", "inject"], 1.0),

    # Reverse
    TriageRule("reverse", ["exe", "dll", "so", "dylib", "sys"], ["reverse", "crack", "keygen", "serial", "license", "password check"], 1.0),
    TriageRule("reverse", ["apk", "dex", "smali", "jar", "class"], ["android", "apk", "java", "smali"], 1.0),
    TriageRule("reverse", ["pyc", "pyo"], ["python", "bytecode", "decompile"], 1.0),
    TriageRule("reverse", [".wasm"], ["wasm", "webassembly"], 1.0),

    # Crypto
    TriageRule("crypto", ["pem", "key", "crt", "cer", "der"], ["rsa", "aes", "des", "ecb", "cbc", "ctr", "gcm", "oracle", "padding"], 1.0),
    TriageRule("crypto", [".py", ".sage"], ["crypto", "encrypt", "decrypt", "cipher", "modulo", "prime", "factor", "discrete log"], 1.0),

    # MISC
    TriageRule("misc", ["png", "jpg", "jpeg", "gif", "bmp", "wav", "mp3", "mp4", "avi"], ["stego", "hidden", "lsb", "exif", "metadata", "watermark"], 1.0),
    TriageRule("misc", ["pcap", "pcapng", "cap"], ["pcap", "wireshark", "traffic", "network", "packet"], 1.0),
    TriageRule("misc", ["zip", "rar", "7z", "tar", "gz", "bz2"], ["archive", "compressed", "zip bomb", "nested", "password protected"], 0.5),
    TriageRule("misc", ["py", "sh", "pl"], ["jail", "sandbox", "escape", "restricted", "pyjail"], 1.0),
    TriageRule("misc", ["qr", "barcode"], ["qr", "barcode", "scan"], 1.0),
    TriageRule("misc", ["txt", "csv", "json", "xml"], ["encode", "base64", "rot13", "morse", "zero-width", "whitespace", "esoteric"], 1.0),

    # Mobile
    TriageRule("mobile", ["apk", "ipa", "aab"], ["android", "ios", "mobile", "app"], 1.0),
    TriageRule("mobile", ["so", "dylib"], ["native", "jni", "frida", "objection"], 0.8),
]


# ─── Solve Patterns by Category ──────────────────────────────────

PWN_PATTERNS: list[SolvePattern] = [
    SolvePattern("strings_first", "Run strings and checksec first to understand the binary", Priority.FIRST,
                 ["strings", "checksec", "file"], "Run file, strings, and checksec on the binary. Look for obvious flags, function names, and security settings."),
    SolvePattern("boF_ret2win", "Simple buffer overflow with win function", Priority.HIGH,
                 ["pwntools", "gdb", "objdump"], "Look for a win function (system, execve, cat flag). Calculate offset with cyclic pattern."),
    SolvePattern("rop_chain", "ROP chain to leak libc and call system", Priority.HIGH,
                 ["pwntools", "ROPgadget", "gdb"], "Leak puts/got address, calculate libc base, return to main, then system('/bin/sh')."),
    SolvePattern("format_string", "Format string vulnerability - leak or write", Priority.HIGH,
                 ["pwntools", "gdb"], "Find format string bug (printf(user_input)). Leak with %p/%x, write with %n."),
    SolvePattern("heap_unsafe_unlink", "Unsafe unlink on older glibc", Priority.MEDIUM,
                 ["pwntools", "gdb"], "Check glibc version. For older versions, classic unsafe unlink. For newer, tcache poisoning or fastbin attack."),
    SolvePattern("house_of_apple2", "House of Apple 2 technique", Priority.MEDIUM,
                 ["pwntools", "gdb"], "For glibc 2.35+. Use _IO_FILE exploitation via House of Apple 2."),
    SolvePattern("got_overwrite", "GOT overwrite via arbitrary write", Priority.MEDIUM,
                 ["pwntools", "gdb", "objdump"], "Partial/total GOT overwrite. Common targets: printf->system, atoi->system."),
    SolvePattern("seccomp_bypass", "Seccomp sandbox bypass", Priority.MEDIUM,
                 ["pwntools", "seccomp-tools"], "Dump seccomp rules. Try open+read+write (orw) shellcode. If execve blocked, use orw."),
    SolvePattern("ret2dlresolve", "ret2dl_resolve for stripped binaries", Priority.LOW,
                 ["pwntools", "gdb"], "For stripped binaries without leaks. Fake Elf64_Rela to resolve system."),
]

WEB_PATTERNS: list[SolvePattern] = [
    SolvePattern("view_source", "View page source and check for comments/hidden fields", Priority.FIRST,
                 ["curl", "browser"], "Check HTML source, JavaScript files, robots.txt, .git/config, and HTTP headers."),
    SolvePattern("ssti_detect", "Server-Side Template Injection detection and exploitation", Priority.HIGH,
                 ["curl", "python", "tplmap"], "Test {{7*7}}, ${7*7}, <%=7*7%>. For Jinja2: use MRO chain for RCE. For Smarty: {system('cmd')}."),
    SolvePattern("sqli_basic", "Basic SQL injection", Priority.HIGH,
                 ["sqlmap", "curl"], "Test ' OR '1'='1. Use sqlmap with --delay=1 --threads=1. Check for UNION, boolean blind, time blind."),
    SolvePattern("ssrf_internal", "SSRF to access internal services", Priority.HIGH,
                 ["curl", "python"], "Try file:///, http://127.0.0.1, http://localhost, gopher://. Check cloud metadata endpoints (169.254.169.254)."),
    SolvePattern("php_loose_comparison", "PHP type juggling / loose comparison", Priority.MEDIUM,
                 ["curl", "python"], "Look for == instead of ===. Magic hashes starting with 0e. JSON bypass with duplicate keys."),
    SolvePattern("jwt_attack", "JWT attacks - none algorithm, key confusion", Priority.MEDIUM,
                 ["curl", "python", "jwt_tool"], "Try alg:none, HMAC/RSA key confusion, weak HMAC secret (rockyou). Use jwt_tool."),
    SolvePattern("java_deser", "Java deserialization", Priority.MEDIUM,
                 ["ysoserial", "curl"], "Look for Base64 rO0AB prefix (Java serialized). Try ysoserial commons-collections, spring beans."),
    SolvePattern("spel_injection", "Spring Expression Language injection", Priority.MEDIUM,
                 ["curl"], "Try ${T(java.lang.Runtime).getRuntime().exec('cmd')}, #{...} syntax."),
    SolvePattern("json_schema_ref", "JSON Schema $ref attack", Priority.LOW,
                 ["curl", "python"], "If API accepts JSON Schema, try $ref to read files or SSRF."),
    SolvePattern("dns_rebinding", "DNS rebinding for SSRF bypass", Priority.LOW,
                 ["python"], "Set up DNS with very short TTL, alternate between allowed and internal IPs."),
]

REVERSE_PATTERNS: list[SolvePattern] = [
    SolvePattern("strings_grep", "Search for flag in strings output first", Priority.FIRST,
                 ["strings", "grep"], "Run strings | grep -i flag. Also search for CTF{, flag{, and common flag patterns in the binary."),
    SolvePattern("objdump_analysis", "Disassemble and identify key functions", Priority.HIGH,
                 ["objdump", "readelf"], "Use objdump -d to find main, check for encryption loops, XOR patterns, and comparison logic."),
    SolvePattern("upx_unpack", "UPX packer detection and unpacking", Priority.HIGH,
                 ["upx", "strings"], "If strings shows UPX!, repair section names (UPX0→.upx0, UPX1→.upx1) then upx -d."),
    SolvePattern("python_replicate", "Replicate algorithm in Python rather than reversing assembly", Priority.HIGH,
                 ["python", "objdump"], "Extract algorithm constants and logic from objdump, reimplement in Python, solve mathematically."),
    SolvePattern("xor_analysis", "XOR-based encryption identification", Priority.HIGH,
                 ["python", "objdump"], "Look for repeated XOR patterns. Common: single-byte XOR, multi-byte XOR, rolling XOR."),
    SolvePattern("splitmix64", "SplitMix64 PRNG identification", Priority.MEDIUM,
                 ["python", "objdump"], "Look for 0x9e3779b97f4a7c15 constant. Replicate the SplitMix64 algorithm in Python."),
    SolvePattern("whitebox_aes", "White-box AES identification", Priority.MEDIUM,
                 ["python"], "Look for large lookup tables (256+ entries). Common: T-box AES, Chow's scheme."),
    SolvePattern("apk_smali_flag", "Search smali for hardcoded flags in Android apps", Priority.HIGH,
                 ["apktool", "grep"], "apktool d app.apk, then grep -r 'flag' smali/ for hardcoded flags (before analyzing .so)."),
    SolvePattern("native_so_identify", "Identify .so functions in Android without running", Priority.HIGH,
                 ["objdump", "python"], "Use objdump on .so to find JNI functions, replicate logic in Python, solve via inverse math."),
    SolvePattern("ocr_extract", "OCR for image-based flags in GUI challenges", Priority.LOW,
                 ["easyocr", "python"], "Use easyocr on screenshots to extract text/flags from GUI applications."),
]

CRYPTO_PATTERNS: list[SolvePattern] = [
    SolvePattern("rsa_basic", "Basic RSA - common factor, small e, Wiener", Priority.FIRST,
                 ["python", "sagemath", "RsaCtfTool"], "Check: shared primes (gcd), small e (root), Wiener (continued fraction), Fermat factoring."),
    SolvePattern("aes_mode", "AES mode attack - ECB oracle, CBC bit flip, padding oracle", Priority.HIGH,
                 ["python", "curl"], "ECB: byte-at-a-time oracle. CBC: bit flip attack, padding oracle (POODLE style). CTR: known plaintext XOR."),
    SolvePattern("prng_crack", "PRNG prediction - LCG, MT19937, LFSR", Priority.HIGH,
                 ["python", "z3"], "Collect outputs, reverse engineer PRNG parameters. MT19937: need 624 consecutive outputs."),
    SolvePattern("lattice_attack", "Lattice reduction for small secrets", Priority.MEDIUM,
                 ["sagemath", "python"], "Hidden number problem, subset sum, LWE with small parameters. Use BKZ/LLL reduction."),
    SolvePattern("hash_length_extension", "Hash length extension attack", Priority.MEDIUM,
                 ["python", "hash_extender"], "MD5/SHA1/SHA256 with secret||message. Use hashpumpy or hash_extender tool."),
    SolvePattern("ecc_small", "ECC with small curve or anomalous curve", Priority.LOW,
                 ["sagemath", "python"], "Check curve order (factor), anomalous curve (Smart attack), MOV attack for small embedding degree."),
    SolvePattern("custom_hash_reverse", "Custom/modified hash - emulate in Unicorn", Priority.MEDIUM,
                 ["unicorn", "python", "objdump"], "Use objdump to find pure arithmetic section (no calls), emulate with Unicorn to reverse."),
]

MISC_PATTERNS: list[SolvePattern] = [
    SolvePattern("unzip_first", "Extract and identify file type first", Priority.FIRST,
                 ["file", "binwalk", "7z"], "Always run file on the challenge first. Then binwalk -e, foremost, or manual extraction."),
    SolvePattern("nested_zip", "Nested archive extraction", Priority.HIGH,
                 ["python", "7z"], "Keep extracting zip/gz/tar layers. Skip at PNG/ELF/TXT. Common: zip inside PNG after PK header."),
    SolvePattern("zero_width", "Zero-width character steganography", Priority.HIGH,
                 ["zero-width-lib", "python"], "Use zero-width-lib (zero-width-lib detect/extract). Don't manually count characters."),
    SolvePattern("png_tail_extract", "PNG with appended data after IEND", Priority.HIGH,
                 ["binwalk", "python", "dd"], "Check for PK (zip) or other headers after PNG IEND chunk. Use dd or python to slice."),
    SolvePattern("lsb_stego", "LSB steganography in images/audio", Priority.HIGH,
                 ["zsteg", "stegsolve", "python"], "Images: zsteg -a. Audio: check LSB of samples. Use stegsolve for visual LSB planes."),
    SolvePattern("pcap_analysis", "PCAP network traffic analysis", Priority.HIGH,
                 ["wireshark", "tshark", "python"], "Extract files (HTTP objects, FTP data). Follow TCP streams. Check for exfiltration patterns (DNS, ICMP)."),
    SolvePattern("pyjail_escape", "Python jail escape techniques", Priority.HIGH,
                 ["python"], "Try: __builtins__, __import__('os').system('sh'), ().__class__.__base__.__subclasses__(), Unicode bypass."),
    SolvePattern("qr_reconstruct", "QR code reconstruction from fragments", Priority.MEDIUM,
                 ["python", "PIL"], "Reconstruct QR from partial images. Know QR format: finder patterns, alignment, timing, data modules."),
    SolvePattern("sdr_decode", "SDR/RF signal decoding", Priority.MEDIUM,
                 ["gqrx", "audacity", "python"], "Load IQ samples, identify modulation (FSK/PSK/QAM), demodulate, decode bits to ASCII."),
    SolvePattern("visual_observation", "Direct visual inspection of frames/images", Priority.MEDIUM,
                 ["python", "PIL", "ffmpeg"], "For video: extract frames with ffmpeg, then visually compare. For images: check edges, color channels."),
    SolvePattern("multi_layer_stego", "Multi-layer nested steganography", Priority.MEDIUM,
                 ["file", "binwalk", "python"], "Layer-by-layer extraction. Each layer produces a different file type. Don't stop after the first extraction."),
]

MOBILE_PATTERNS: list[SolvePattern] = [
    SolvePattern("apktool_decompile", "Decompile APK and search for flags in smali/assets", Priority.FIRST,
                 ["apktool", "grep", "jadx"], "apktool d → grep -ri flag in smali/, assets/, res/raw/. Also check AndroidManifest.xml."),
    SolvePattern("jadx_java", "Decompile to Java with jadx for analysis", Priority.HIGH,
                 ["jadx"], "Use jadx for Java-level analysis. Look at MainActivity, native method declarations."),
    SolvePattern("native_crypto", "Reverse .so native crypto in Python", Priority.HIGH,
                 ["objdump", "python"], "Identify crypto in lib*.so via objdump. Extract constants, replicate in Python. Never run the native code directly."),
    SolvePattern("frida_hook", "Frida dynamic instrumentation hints", Priority.LOW,
                 ["frida", "python", "adb"], "Hook crypto functions, bypass root detection, SSL pinning. For when static analysis isn't enough."),
]

# Category to patterns mapping
CATEGORY_PATTERNS: dict[str, list[SolvePattern]] = {
    "pwn": PWN_PATTERNS,
    "web": WEB_PATTERNS,
    "reverse": REVERSE_PATTERNS,
    "crypto": CRYPTO_PATTERNS,
    "misc": MISC_PATTERNS,
    "mobile": MOBILE_PATTERNS,
}


# ─── Universal Tactics ───────────────────────────────────────────

UNIVERSAL_TACTICS = [
    "Always run `file` and `strings` first on any unknown file.",
    "If stuck, check if there's a simpler interpretation — don't over-analyze.",
    "Prefer direct observation over automated tools for simple challenges.",
    "When a tool produces no results in 60 seconds, try a different approach.",
    "Check for nested layers: archives within files, files within archives.",
    "Look for plaintext flags in the most obvious places before reaching for heavy tools.",
    "Rate-limit all network requests (nmap -T2, sqlmap --delay=1 --threads=1, dirb -t 2).",
    "For any file: check header bytes to verify actual type vs extension.",
    "Screenshot every key step for writeup generation.",
    "If a complex approach fails, try the simplest possible attack first.",
]

SAFETY_RULES = [
    "Never run untrusted binaries natively — always analyze in Docker container.",
    "Rate-limit network tools: nmap -T2/-T3, sqlmap --delay=1 --threads=1, dirb -t 2.",
    "No high-concurrency scans against remote targets.",
    "Only exploit services you are authorized to test.",
    "Never exfiltrate or retain target data beyond the flag.",
    "Clean up all artifacts after solving (containers, temp files, connections).",
]

WRITEUP_SECTIONS = [
    ("Challenge Info", ["Name", "Category", "Points", "Files Provided"]),
    ("Solution Overview", ["Summary of the approach in 1-2 sentences"]),
    ("Information Gathering", ["Initial analysis steps", "file/strings results", "Key observations"]),
    ("Vulnerability Analysis", ["Identified weakness", "Tools used for analysis"]),
    ("Exploitation", ["Step-by-step exploit process", "Code snippets", "Screenshots of key steps"]),
    ("Flag", ["The captured flag"]),
    ("Lessons Learned", ["What this challenge taught", "Applicable patterns for future challenges"]),
]
