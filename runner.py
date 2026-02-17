import os
import sys
import subprocess
import shutil
import json
import re

# ─── CORES ───────────────────────────────────
R  = "\033[31m"
G  = "\033[32m"
Y  = "\033[33m"
B  = "\033[34m"
M  = "\033[35m"
C  = "\033[36m"
W  = "\033[37m"
BO = "\033[1m"
X  = "\033[0m"

def ok(m):   print(f"{G}✅ {m}{X}")
def err(m):  print(f"{R}❌ {m}{X}")
def info(m): print(f"{C}➜  {m}{X}")
def warn(m): print(f"{Y}⚠️  {m}{X}")
def ask(m):  return input(f"{M}{BO}{m}{X} ").strip()

# ─── BANNER ──────────────────────────────────
def banner():
    os.system("clear")
    print(f"""{M}{BO}
╔══════════════════════════════════════════════╗
║          🤖  BOT RUNNER  🤖                 ║
║   Clona, configura e inicia seu bot          ║
╚══════════════════════════════════════════════╝{X}
""")

# ─── CHECAR DEPENDÊNCIAS ─────────────────────
def check_deps():
    info("Verificando dependências do sistema...")

    # git
    if not shutil.which("git"):
        warn("Git não encontrado. Instalando...")
        os.system("pkg install git -y")

    # node
    if not shutil.which("node"):
        warn("Node.js não encontrado. Instalando...")
        os.system("pkg install nodejs -y")

    # npm
    if not shutil.which("npm"):
        warn("npm não encontrado. Instalando...")
        os.system("pkg install nodejs -y")

    ok("Dependências OK!")

# ─── CLONAR REPO ─────────────────────────────
def clone_repo(url):
    # Normalizar URL
    url = url.strip().rstrip("/")
    if not url.startswith("http"):
        url = "https://github.com/" + url
    if not url.endswith(".git"):
        url += ".git"

    repo_name = url.split("/")[-1].replace(".git", "")
    clone_path = os.path.join(os.getcwd(), repo_name)

    # Remover se já existir
    if os.path.exists(clone_path):
        warn(f'Pasta "{repo_name}" já existe. Removendo...')
        shutil.rmtree(clone_path)

    info(f"Clonando: {url}")
    result = subprocess.run(["git", "clone", url], capture_output=False)

    if result.returncode != 0:
        err("Falha ao clonar! Verifique se o link está correto e o repo é público.")
        sys.exit(1)

    ok(f"Repositório clonado em: {clone_path}")
    return clone_path

# ─── INJETAR TOKEN E CLIENT ID ───────────────
def inject_credentials(folder, token, client_id, guild_id=None):
    info("Injetando credenciais nos arquivos...")

    extensions = [".js", ".ts", ".env", ".json", ".py"]
    substituicoes = 0

    for root, dirs, files in os.walk(folder):
        # ignorar node_modules e .git
        dirs[:] = [d for d in dirs if d not in ["node_modules", ".git", "__pycache__"]]

        for fname in files:
            fpath = os.path.join(root, fname)
            ext = os.path.splitext(fname)[1]

            if ext not in extensions and fname != ".env":
                continue

            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                original = content

                # Substituir placeholders comuns de TOKEN
                token_patterns = [
                    r"SEU_TOKEN_AQUI",
                    r"YOUR_TOKEN_HERE",
                    r"BOT_TOKEN_HERE",
                    r"TOKEN_HERE",
                    r"seu-token-aqui",
                    r"your-token-here",
                ]
                for p in token_patterns:
                    content = re.sub(p, token, content, flags=re.IGNORECASE)

                # Substituir placeholders de CLIENT_ID
                id_patterns = [
                    r"SEU_CLIENT_ID_AQUI",
                    r"YOUR_CLIENT_ID_HERE",
                    r"CLIENT_ID_HERE",
                    r"seu-client-id-aqui",
                    r"your-client-id-here",
                    r"APPLICATION_ID_HERE",
                ]
                for p in id_patterns:
                    content = re.sub(p, client_id, content, flags=re.IGNORECASE)

                # Guild ID se fornecido
                if guild_id:
                    guild_patterns = [
                        r"SEU_GUILD_ID_AQUI",
                        r"YOUR_GUILD_ID_HERE",
                        r"GUILD_ID_HERE",
                        r"seu-guild-id-aqui",
                    ]
                    for p in guild_patterns:
                        content = re.sub(p, guild_id, content, flags=re.IGNORECASE)

                if content != original:
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write(content)
                    substituicoes += 1
                    ok(f"Credenciais injetadas em: {fname}")

            except Exception as e:
                warn(f"Não foi possível processar {fname}: {e}")

    # Criar/atualizar .env também
    env_path = os.path.join(folder, ".env")
    env_content = f"DISCORD_TOKEN={token}\nCLIENT_ID={client_id}\n"
    if guild_id:
        env_content += f"GUILD_ID={guild_id}\n"
    with open(env_path, "w") as f:
        f.write(env_content)
    ok(".env criado/atualizado!")

    info(f"Total de arquivos com credenciais injetadas: {substituicoes}")

# ─── DETECTAR PROJETO ────────────────────────
def detect_project(folder):
    files = os.listdir(folder)

    if "package.json" in files:
        pkg_path = os.path.join(folder, "package.json")
        with open(pkg_path, "r") as f:
            pkg = json.load(f)
        main = pkg.get("main", "index.js")
        scripts = pkg.get("scripts", {})
        start_script = scripts.get("start")
        return {
            "type": "node",
            "install": "npm install",
            "start": "npm start" if start_script else f"node {main}",
        }

    py_entries = ["main.py", "app.py", "bot.py", "run.py", "start.py", "index.py"]
    py_entry = next((f for f in py_entries if f in files), None)
    if not py_entry:
        py_entry = next((f for f in files if f.endswith(".py")), None)

    if py_entry:
        has_reqs = "requirements.txt" in files
        return {
            "type": "python",
            "install": f"pip install -r requirements.txt" if has_reqs else None,
            "start": f"python {py_entry}",
        }

    return None

# ─── INSTALAR DEPENDÊNCIAS ───────────────────
def install_deps(project, folder):
    if not project.get("install"):
        return

    info(f"Instalando dependências: {project['install']}")
    result = subprocess.run(
        project["install"],
        shell=True,
        cwd=folder
    )

    if result.returncode == 0:
        ok("Dependências instaladas!")
    else:
        warn("Algumas dependências falharam. Tentando continuar mesmo assim...")

# ─── MOSTRAR ARQUIVOS ────────────────────────
def show_files(folder):
    print(f"\n{B}📂 Arquivos do projeto:{X}")
    for f in os.listdir(folder):
        if f not in ["node_modules", ".git", "__pycache__"]:
            print(f"  {W}└ {f}{X}")
    print()

# ─── EXECUTAR BOT ────────────────────────────
def run_bot(project, folder):
    print(f"\n{G}{'━'*46}{X}")
    info(f"▶️  Executando: {project['start']}")
    print(f"{G}{'━'*46}{X}\n")

    try:
        proc = subprocess.Popen(
            project["start"],
            shell=True,
            cwd=folder
        )
        proc.wait()
    except KeyboardInterrupt:
        warn("Bot encerrado pelo usuário (Ctrl+C).")

# ─── MAIN ────────────────────────────────────
def main():
    banner()
    check_deps()

    print(f"\n{BO}{C}{'─'*46}")
    print("  📋  CONFIGURAÇÃO DO BOT")
    print(f"{'─'*46}{X}\n")

    # Perguntar dados
    repo_url  = ask("🔗 Link do repositório GitHub:")
    token     = ask("🔑 Token do bot Discord:")
    client_id = ask("🆔 Client ID (Application ID) do bot:")

    print(f"\n{Y}Guild ID é opcional (deixe em branco para pular){X}")
    guild_id = ask("🏠 Guild ID do servidor (opcional):")
    if not guild_id:
        guild_id = None

    print(f"\n{C}{'─'*46}{X}")
    print(f"  {W}Repositório : {C}{repo_url}{X}")
    print(f"  {W}Token       : {C}{token[:10]}...{token[-4:]}{X}")
    print(f"  {W}Client ID   : {C}{client_id}{X}")
    if guild_id:
        print(f"  {W}Guild ID    : {C}{guild_id}{X}")
    print(f"{C}{'─'*46}{X}\n")

    confirma = ask("✅ Confirmar e iniciar? (s/n):").lower()
    if confirma not in ["s", "sim", "y", "yes"]:
        warn("Cancelado.")
        sys.exit(0)

    # Executar etapas
    print()
    folder = clone_repo(repo_url)
    inject_credentials(folder, token, client_id, guild_id)

    project = detect_project(folder)
    if not project:
        err("Não consegui detectar o tipo de projeto automaticamente.")
        show_files(folder)
        sys.exit(1)

    ok(f"Projeto detectado: {project['type'].upper()}")
    show_files(folder)
    install_deps(project, folder)
    run_bot(project, folder)

if __name__ == "__main__":
    main()
