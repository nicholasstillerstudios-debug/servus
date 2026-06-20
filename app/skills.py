"""Sistema de Skills do SERVUS.

Cada skill = pasta com SKILL.md (frontmatter YAML simples + corpo markdown).
Skills sao clonadas via git e injetadas no system_message do interpreter
quando ativadas. Compativel com o formato .claude/skills do Claude.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import httpx


# --- localizacao das skills ---------------------------------------------

def skills_dir() -> Path:
    """Onde as skills vivem.

    - Modo instalado (PyInstaller): %APPDATA%\\Servus\\skills
    - Modo dev: <projeto>\\skills
    """
    if getattr(sys, "frozen", False):
        base = Path(os.environ.get("APPDATA", str(Path.home()))) / "Servus"
    else:
        base = Path(__file__).parent.parent
    d = base / "skills"
    d.mkdir(parents=True, exist_ok=True)
    return d


# --- modelo --------------------------------------------------------------

@dataclass
class Skill:
    name: str
    path: Path
    description: str
    content: str       # corpo do SKILL.md (instrucoes)
    source: str = ""   # url git, se conhecido

    def to_dict(self, enabled: bool = False) -> dict:
        return {
            "name": self.name,
            "path": str(self.path),
            "description": self.description,
            "source": self.source,
            "enabled": enabled,
            "tokens_estimate": _estimate_tokens(self.content),
        }


def _estimate_tokens(text: str) -> int:
    # ~4 chars por token e suficiente como aproximacao
    return max(1, len(text) // 4)


# --- parser de SKILL.md --------------------------------------------------

_FRONT_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


def parse_skill_md(text: str) -> tuple[dict, str]:
    """Parse frontmatter YAML simples (key: value, sem aninhamento) + corpo."""
    m = _FRONT_RE.match(text)
    if not m:
        return {}, text.strip()
    front_text, body = m.group(1), m.group(2)
    front: dict[str, str] = {}
    for line in front_text.splitlines():
        if ":" in line and not line.lstrip().startswith("#"):
            k, _, v = line.partition(":")
            front[k.strip()] = v.strip().strip("\"'")
    return front, body.strip()


def _read_skill(folder: Path, source_file: Path = Path(".source")) -> Skill | None:
    md = folder / "SKILL.md"
    if not md.exists():
        # tenta encontrar SKILL.md em subpasta
        nested = list(folder.rglob("SKILL.md"))
        if not nested:
            return None
        md = nested[0]
    try:
        text = md.read_text(encoding="utf-8")
    except Exception:
        return None
    front, body = parse_skill_md(text)
    name = front.get("name") or folder.name
    desc = front.get("description") or front.get("when_to_use") or ""
    src_path = folder / source_file.name
    source = src_path.read_text(encoding="utf-8").strip() if src_path.exists() else ""
    return Skill(
        name=name,
        path=folder,
        description=desc,
        content=body,
        source=source,
    )


# --- API publica ---------------------------------------------------------

def list_skills() -> list[Skill]:
    out: list[Skill] = []
    for entry in sorted(skills_dir().iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        s = _read_skill(entry)
        if s:
            out.append(s)
    return out


def find_skill(name: str) -> Skill | None:
    for s in list_skills():
        if s.name == name or s.path.name == name:
            return s
    return None


def install_from_git(url: str) -> Skill:
    """Clona <url> em skills/<repo-name>. Falha se git nao estiver instalado."""
    url = url.strip()
    if not url:
        raise ValueError("URL vazia")
    repo = url.rstrip("/").split("/")[-1].removesuffix(".git")
    target = skills_dir() / repo
    if target.exists():
        raise ValueError(f"Skill ja instalada: {repo}")

    if not _has_git():
        # fallback: github zipball
        return _install_from_zip(url, target)

    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", url, str(target)],
            check=True, capture_output=True, text=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"git clone falhou: {e.stderr.strip() or e}")

    (target / ".source").write_text(url, encoding="utf-8")
    s = _read_skill(target)
    if not s:
        shutil.rmtree(target, ignore_errors=True)
        raise RuntimeError("Repo nao contem SKILL.md")
    return s


def _install_from_zip(url: str, target: Path) -> Skill:
    """Fallback sem git: baixa zipball do GitHub."""
    import io
    import zipfile

    m = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    if not m:
        raise RuntimeError("Sem git instalado e URL nao e GitHub")
    user, repo = m.group(1), m.group(2)
    zip_url = f"https://api.github.com/repos/{user}/{repo}/zipball"
    r = httpx.get(zip_url, follow_redirects=True, timeout=60)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        target.mkdir(parents=True, exist_ok=True)
        # zipball tem um diretorio raiz tipo user-repo-sha/; achatamos
        root = zf.namelist()[0].split("/")[0]
        for member in zf.namelist():
            if member.endswith("/"):
                continue
            rel = member[len(root) + 1:] if member.startswith(root + "/") else member
            if not rel:
                continue
            out = target / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(zf.read(member))
    (target / ".source").write_text(url, encoding="utf-8")
    s = _read_skill(target)
    if not s:
        shutil.rmtree(target, ignore_errors=True)
        raise RuntimeError("Repo nao contem SKILL.md")
    return s


def remove(name: str) -> None:
    target = skills_dir() / name
    if not target.exists():
        # tenta achar por skill name
        for s in list_skills():
            if s.name == name:
                target = s.path
                break
    if not target.exists():
        raise FileNotFoundError(f"Skill nao encontrada: {name}")
    shutil.rmtree(target)


def update(name: str) -> None:
    target = skills_dir() / name
    if not (target / ".git").exists():
        raise RuntimeError("Skill nao foi instalada via git")
    if not _has_git():
        raise RuntimeError("git nao instalado")
    subprocess.run(["git", "-C", str(target), "pull"], check=True, capture_output=True)


# --- descoberta de skills locais ----------------------------------------

DISCOVERY_PATHS = [
    Path.home() / ".claude" / "skills",
    Path.home() / "OneDrive" / "Desktop" / ".claude" / "skills",
    Path.home() / "AppData" / "Roaming" / "Claude" / "skills",
]


def discover_local() -> list[dict]:
    """Procura SKILL.md nos paths conhecidos. Retorna candidatos NAO instalados."""
    installed_names = {s.name for s in list_skills()}
    installed_real_paths = {s.path.resolve() for s in list_skills()}
    out: list[dict] = []
    seen: set[str] = set()

    for base in DISCOVERY_PATHS:
        if not base.exists():
            continue
        for md in base.rglob("SKILL.md"):
            folder = md.parent
            if folder.resolve() in installed_real_paths:
                continue
            try:
                text = md.read_text(encoding="utf-8")
            except Exception:
                continue
            front, body = parse_skill_md(text)
            name = front.get("name") or folder.name
            if name in installed_names or name in seen:
                continue
            seen.add(name)
            # grupo = pasta intermediaria entre o base e a skill (ex: composio-skills)
            try:
                rel = folder.relative_to(base)
                group = rel.parts[0] if len(rel.parts) > 1 else "(raiz)"
            except Exception:
                group = "(outro)"
            out.append({
                "name": name,
                "path": str(folder),
                "description": front.get("description", ""),
                "tokens_estimate": _estimate_tokens(body),
                "source_root": str(base),
                "group": group,
            })
    return sorted(out, key=lambda x: (x["group"], x["name"]))


def import_local(source_path: str) -> Skill:
    """Copia uma skill local (pasta) pra skills/."""
    src = Path(source_path)
    if not src.exists() or not src.is_dir():
        raise FileNotFoundError(f"Pasta nao encontrada: {source_path}")
    if not (src / "SKILL.md").exists():
        raise FileNotFoundError(f"SKILL.md nao encontrado em {source_path}")

    dest = skills_dir() / src.name
    n = 1
    base_dest = dest
    while dest.exists():
        dest = base_dest.with_name(f"{base_dest.name}-{n}")
        n += 1

    shutil.copytree(src, dest)
    (dest / ".source").write_text(f"local:{src}", encoding="utf-8")
    s = _read_skill(dest)
    if not s:
        shutil.rmtree(dest, ignore_errors=True)
        raise RuntimeError("Skill invalida apos copia")
    return s


def _has_git() -> bool:
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


# --- injecao no system_message ------------------------------------------

def render_for_prompt(enabled_names: list[str]) -> str:
    """Gera o trecho do system_message com as skills ativas."""
    if not enabled_names:
        return ""
    enabled = [s for s in list_skills() if s.name in enabled_names or s.path.name in enabled_names]
    if not enabled:
        return ""
    blocks = ["\n\n### Skills disponiveis\n"]
    blocks.append(
        "Voce tem acesso as seguintes skills. Use-as quando o pedido se "
        "encaixar na descricao. Os arquivos auxiliares de cada skill estao "
        "no campo 'path'.\n"
    )
    for s in enabled:
        blocks.append(
            f"\n#### {s.name}\n"
            f"_quando usar:_ {s.description}\n"
            f"_path:_ `{s.path}`\n\n"
            f"{s.content}\n"
            f"---\n"
        )
    return "".join(blocks)


__all__ = [
    "Skill",
    "skills_dir",
    "list_skills",
    "find_skill",
    "install_from_git",
    "discover_local",
    "import_local",
    "remove",
    "update",
    "render_for_prompt",
]
