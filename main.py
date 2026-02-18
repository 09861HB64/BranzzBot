import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import os
import json
import datetime
from threading import Thread
from flask import Flask, jsonify, render_template_string, request
import time

# ============================================================
# CONFIGURAÇÕES
# ============================================================
TOKEN = os.environ.get("DISCORD_TOKEN", "SEU_TOKEN_AQUI")
BOT_START_TIME = time.time()
bot_running = True

# ============================================================
# FLASK - PAINEL WEB (UptimeRobot + Dashboard)
# ============================================================
app = Flask(__name__)

HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Bot Dashboard</title>
  <style>
    * { margin:0; padding:0; box-sizing:border-box; }
    body { background:#0d0d0d; color:#e0e0e0; font-family:'Segoe UI',sans-serif; min-height:100vh; display:flex; flex-direction:column; align-items:center; }
    header { width:100%; background:linear-gradient(90deg,#5865F2,#7289da); padding:22px 40px; display:flex; align-items:center; gap:16px; box-shadow:0 4px 20px #0008; }
    header h1 { font-size:1.7rem; font-weight:700; color:#fff; letter-spacing:1px; }
    .badge { background:#23272a; color:#43b581; border-radius:20px; padding:4px 14px; font-size:.85rem; font-weight:600; border:1.5px solid #43b581; }
    .badge.offline { color:#f04747; border-color:#f04747; }
    .container { width:100%; max-width:900px; padding:36px 20px; display:flex; flex-direction:column; gap:24px; }
    .card { background:#1a1a2e; border-radius:14px; padding:28px 32px; box-shadow:0 2px 16px #0006; border:1px solid #2a2a4a; }
    .card h2 { font-size:1.1rem; color:#7289da; margin-bottom:18px; display:flex; align-items:center; gap:8px; }
    .stat-row { display:flex; flex-wrap:wrap; gap:18px; }
    .stat { flex:1; min-width:150px; background:#16213e; border-radius:10px; padding:18px 20px; text-align:center; border:1px solid #2a2a5a; }
    .stat .val { font-size:2rem; font-weight:700; color:#5865F2; }
    .stat .label { font-size:.8rem; color:#aaa; margin-top:4px; }
    .btn { display:inline-block; padding:11px 28px; border-radius:8px; font-size:.95rem; font-weight:600; cursor:pointer; border:none; transition:.2s; }
    .btn-green { background:#43b581; color:#fff; }
    .btn-green:hover { background:#3ca374; }
    .btn-red { background:#f04747; color:#fff; }
    .btn-red:hover { background:#d93636; }
    .btn-blue { background:#5865F2; color:#fff; }
    .btn-blue:hover { background:#4752c4; }
    .actions { display:flex; gap:14px; flex-wrap:wrap; }
    .log-box { background:#0d0d0d; border-radius:8px; padding:14px 18px; font-family:monospace; font-size:.82rem; color:#43b581; max-height:200px; overflow-y:auto; border:1px solid #2a2a4a; }
    .status-dot { width:10px; height:10px; border-radius:50%; background:#43b581; display:inline-block; margin-right:6px; animation:pulse 1.5s infinite; }
    .status-dot.off { background:#f04747; animation:none; }
    @keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:.4;} }
    footer { margin-top:auto; padding:18px; color:#555; font-size:.8rem; }
  </style>
</head>
<body>
  <header>
    <div class="status-dot" id="sdot"></div>
    <h1>🤖 Discord Bot — Dashboard</h1>
    <span class="badge" id="statusBadge">ONLINE</span>
  </header>
  <div class="container">
    <div class="card">
      <h2>📊 Estatísticas</h2>
      <div class="stat-row">
        <div class="stat"><div class="val" id="uptime">--</div><div class="label">Uptime</div></div>
        <div class="stat"><div class="val" id="guilds">--</div><div class="label">Servidores</div></div>
        <div class="stat"><div class="val" id="users">--</div><div class="label">Usuários</div></div>
        <div class="stat"><div class="val" id="latency">--</div><div class="label">Latência (ms)</div></div>
      </div>
    </div>
    <div class="card">
      <h2>⚙️ Controles</h2>
      <div class="actions">
        <button class="btn btn-blue" onclick="fetchStats()">🔄 Atualizar</button>
        <button class="btn btn-red" onclick="controlBot('stop')">⏹ Desligar Bot</button>
        <button class="btn btn-green" onclick="controlBot('restart')">🔁 Reiniciar Bot</button>
      </div>
    </div>
    <div class="card">
      <h2>📜 Log de Atividade</h2>
      <div class="log-box" id="logBox">Aguardando logs...</div>
    </div>
  </div>
  <footer>Bot Dashboard &copy; 2025 — Powered by discord.py</footer>
  <script>
    const logs = [];
    function addLog(msg) {
      const t = new Date().toLocaleTimeString('pt-BR');
      logs.unshift(`[${t}] ${msg}`);
      if(logs.length>40) logs.pop();
      document.getElementById('logBox').innerText = logs.join('\\n');
    }
    async function fetchStats() {
      try {
        const r = await fetch('/api/stats');
        const d = await r.json();
        document.getElementById('uptime').innerText = d.uptime;
        document.getElementById('guilds').innerText = d.guilds;
        document.getElementById('users').innerText = d.users;
        document.getElementById('latency').innerText = d.latency;
        const online = d.status === 'online';
        document.getElementById('statusBadge').innerText = online ? 'ONLINE' : 'OFFLINE';
        document.getElementById('statusBadge').className = 'badge' + (online?'':' offline');
        document.getElementById('sdot').className = 'status-dot' + (online?'':' off');
        addLog(`Stats atualizadas — ${d.guilds} servidor(es), latência ${d.latency}ms`);
      } catch(e) { addLog('Erro ao buscar stats'); }
    }
    async function controlBot(action) {
      if(action==='stop' && !confirm('Deseja desligar o bot?')) return;
      if(action==='restart' && !confirm('Deseja reiniciar o bot?')) return;
      try {
        const r = await fetch('/api/control', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({action})});
        const d = await r.json();
        addLog(`Ação: ${action} — ${d.message}`);
        setTimeout(fetchStats, 3000);
      } catch(e) { addLog('Erro ao enviar comando'); }
    }
    fetchStats();
    setInterval(fetchStats, 30000);
    addLog('Dashboard carregado com sucesso!');
  </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_DASHBOARD)

@app.route("/ping")
def ping():
    return "OK", 200

@app.route("/api/stats")
def api_stats():
    uptime_sec = int(time.time() - BOT_START_TIME)
    h = uptime_sec // 3600
    m = (uptime_sec % 3600) // 60
    s = uptime_sec % 60
    uptime_str = f"{h}h {m}m {s}s"
    try:
        guilds = len(bot.guilds)
        users = sum(g.member_count or 0 for g in bot.guilds)
        latency = round(bot.latency * 1000)
        status = "online"
    except Exception:
        guilds = 0; users = 0; latency = 0; status = "offline"
    return jsonify({"status": status, "uptime": uptime_str, "guilds": guilds, "users": users, "latency": latency})

@app.route("/api/control", methods=["POST"])
def api_control():
    global bot_running
    data = request.get_json() or {}
    action = data.get("action", "")
    if action == "stop":
        bot_running = False
        asyncio.run_coroutine_threadsafe(bot.close(), bot.loop)
        return jsonify({"message": "Bot desligado."})
    elif action == "restart":
        bot_running = True
        return jsonify({"message": "Reinicialização solicitada. Por favor reinicie o processo manualmente no Replit."})
    return jsonify({"message": "Ação desconhecida."}), 400

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# ============================================================
# BOT DISCORD
# ============================================================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Storage em memória (persiste enquanto o bot roda)
# { guild_id: { "support_role_id": int, "support_users": [ids], "tickets": {channel_id: {...}} } }
guild_data = {}

def get_gd(guild_id):
    if guild_id not in guild_data:
        guild_data[guild_id] = {"support_role_id": None, "support_users": [], "tickets": {}}
    return guild_data[guild_id]

# ============================================================
# EVENTOS
# ============================================================
@bot.event
async def on_ready():
    print(f"✅ Bot online como {bot.user}")
    await tree.sync()
    auto_close_tickets.start()

@bot.event
async def on_member_join(member: discord.Member):
    guild = member.guild
    gd = get_gd(guild.id)
    # Auto role de Membro
    member_role = discord.utils.get(guild.roles, name="Membro")
    if member_role:
        try:
            await member.add_roles(member_role)
        except Exception:
            pass
    # Boas-vindas
    welcome_ch = discord.utils.get(guild.text_channels, name="「👋」boas-vindas")
    if not welcome_ch:
        welcome_ch = discord.utils.get(guild.text_channels, name="boas-vindas")
    if welcome_ch:
        embed = discord.Embed(
            title=f"✨ Bem-vindo(a) ao {guild.name}!",
            description=f"Olá {member.mention}, seja muito bem-vindo(a) ao nosso servidor!\n\nEsperamos que você aproveite bastante. Leia as regras e divirta-se! 🎉",
            color=0x5865F2,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        if guild.icon:
            embed.set_image(url=guild.icon.url)
        embed.set_footer(text=f"Membro #{guild.member_count}")
        await welcome_ch.send(embed=embed)

# ============================================================
# TASK: fechar tickets sem assumir após 12h / auto-close após 19h
# ============================================================
@tasks.loop(minutes=5)
async def auto_close_tickets():
    now = datetime.datetime.utcnow()
    for guild_id, gd in guild_data.items():
        guild = bot.get_guild(guild_id)
        if not guild:
            continue
        to_close = []
        for ch_id, tinfo in list(gd["tickets"].items()):
            ch = guild.get_channel(ch_id)
            if not ch:
                to_close.append(ch_id)
                continue
            opened_at = tinfo.get("opened_at")
            assumed = tinfo.get("assumed", False)
            if not opened_at:
                continue
            delta = (now - opened_at).total_seconds()
            # 12h sem assumir → log
            if not assumed and delta > 43200 and not tinfo.get("warned_12h"):
                tinfo["warned_12h"] = True
                log_ch = discord.utils.get(guild.text_channels, name="「📋」logs-tickets")
                if log_ch:
                    embed = discord.Embed(
                        title="⚠️ Ticket sem atendimento",
                        description=f"O ticket {ch.mention} está aberto há mais de 12 horas sem que nenhum admin o assumiu.",
                        color=0xffa500,
                        timestamp=now
                    )
                    await log_ch.send(embed=embed)
            # 19h assumed → auto-close
            if assumed and delta > 68400 and not tinfo.get("auto_closing"):
                tinfo["auto_closing"] = True
                await ch.send("⏰ Este ticket será fechado automaticamente em 6 segundos por inatividade (19h).")
                await asyncio.sleep(6)
                await _close_ticket_channel(guild, ch, tinfo, "Auto-close por inatividade (19h)")
                to_close.append(ch_id)
        for ch_id in to_close:
            gd["tickets"].pop(ch_id, None)

async def _close_ticket_channel(guild, channel, tinfo, motivo):
    log_ch = discord.utils.get(guild.text_channels, name="「📋」logs-tickets")
    opener_id = tinfo.get("opener_id")
    opener = guild.get_member(opener_id) if opener_id else None
    embed = discord.Embed(
        title="🔒 Ticket Fechado",
        description=f"**Ticket:** {channel.name}\n**Motivo:** {motivo}\n**Aberto por:** {opener.mention if opener else 'Desconhecido'}",
        color=0xf04747,
        timestamp=datetime.datetime.utcnow()
    )
    if log_ch:
        await log_ch.send(embed=embed)
    # DM para quem abriu
    if opener:
        try:
            await opener.send(embed=embed)
        except Exception:
            pass
    # DM para owner
    if guild.owner:
        try:
            await guild.owner.send(embed=embed)
        except Exception:
            pass
    try:
        await channel.delete(reason=motivo)
    except Exception:
        pass
    # Apagar categoria se vazia
    cat = channel.category
    if cat and len(cat.channels) == 0:
        try:
            await cat.delete()
        except Exception:
            pass

# ============================================================
# COMANDO /create — SETUP COMPLETO DO SERVIDOR
# ============================================================
@tree.command(name="create", description="Configura todo o servidor (apenas dono)")
async def create_command(interaction: discord.Interaction):
    guild = interaction.guild
    if interaction.user.id != guild.owner_id:
        await interaction.response.send_message("❌ Apenas o **dono do servidor** pode usar este comando!", ephemeral=True)
        return

    await interaction.response.send_message("⚙️ Iniciando configuração completa do servidor...", ephemeral=True)

    # ── Limpar categorias existentes (opcional - comentado para segurança)
    # for cat in guild.categories: await cat.delete()

    # ── CARGOS ──
    perms_everyone = discord.Permissions(
        read_messages=False, send_messages=False
    )

    # Cargo Membro
    member_role = discord.utils.get(guild.roles, name="Membro")
    if not member_role:
        member_role = await guild.create_role(
            name="Membro",
            color=discord.Color.from_str("#7289da"),
            permissions=discord.Permissions(
                read_messages=True, send_messages=True, read_message_history=True,
                attach_files=True, embed_links=True, add_reactions=True, use_application_commands=True
            ),
            reason="Setup automático"
        )

    # Cargo Support
    support_role = discord.utils.get(guild.roles, name="╔ Support")
    if not support_role:
        support_role = await guild.create_role(
            name="╔ Support",
            color=discord.Color.green(),
            permissions=discord.Permissions(
                read_messages=True, send_messages=True, manage_channels=True,
                read_message_history=True, attach_files=True, embed_links=True,
                manage_messages=True, use_application_commands=True
            ),
            reason="Setup automático"
        )

    # Cargo Owner/Woner
    owner_role = discord.utils.get(guild.roles, name="👑 Owner")
    if not owner_role:
        owner_role = await guild.create_role(
            name="👑 Owner",
            color=discord.Color.gold(),
            permissions=discord.Permissions(administrator=True),
            reason="Setup automático"
        )

    # Dar cargo Owner para o dono
    try:
        owner_member = guild.get_member(guild.owner_id)
        if owner_member:
            await owner_member.add_roles(owner_role, support_role)
    except Exception:
        pass

    # Salvar support role
    gd = get_gd(guild.id)
    gd["support_role_id"] = support_role.id

    # @everyone sem permissões
    await guild.default_role.edit(permissions=discord.Permissions(read_messages=False, send_messages=False))

    # Overwrites base para canais públicos
    def pub_ow():
        return {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

    def info_ow():  # canais info onde ninguém digita
        return {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            support_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

    # ── CATEGORIA: TOPO (Informações fixas) ──
    cat_topo = await guild.create_category("┏━━ 📌 INFORMAÇÕES ━━┓", position=0)
    ch_invites = await guild.create_text_channel("「🔗」convite", category=cat_topo, overwrites=info_ow())
    ch_members = await guild.create_text_channel("「👥」membros", category=cat_topo, overwrites=info_ow())
    ch_welcome = await guild.create_text_channel("「👋」boas-vindas", category=cat_topo, overwrites={
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
        support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    })

    # ── CATEGORIA: CHAT ──
    cat_chat = await guild.create_category("┣━━ 💬 CHAT ━━┫")
    chat_ow = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True),
        support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    await guild.create_text_channel("「💬」geral", category=cat_chat, overwrites=chat_ow)
    await guild.create_text_channel("「😂」memes", category=cat_chat, overwrites=chat_ow)
    await guild.create_text_channel("「🎮」jogos", category=cat_chat, overwrites=chat_ow)

    # ── CATEGORIA: MÍDIA ──
    cat_media = await guild.create_category("┣━━ 📸 MÍDIA ━━┫")
    media_ow = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
        support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    await guild.create_text_channel("「📸」fotos", category=cat_media, overwrites=media_ow)
    await guild.create_text_channel("「🎬」vídeos", category=cat_media, overwrites=media_ow)
    await guild.create_text_channel("「🎵」músicas", category=cat_media, overwrites=media_ow)

    # ── CATEGORIA: COMANDOS ──
    cat_cmds = await guild.create_category("┣━━ ⚡ COMANDOS ━━┫")
    cmd_ow = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, use_application_commands=True),
        support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    await guild.create_text_channel("「⚡」bot-cmds", category=cat_cmds, overwrites=cmd_ow)
    ch_hits = await guild.create_text_channel("「🏆」hits", category=cat_cmds, overwrites=pub_ow())
    ch_tutorial = await guild.create_text_channel("「📖」tutorial-key", category=cat_cmds, overwrites=pub_ow())
    ch_logs_user = await guild.create_text_channel("「📝」criar-log", category=cat_cmds, overwrites=chat_ow)

    # ── CATEGORIA: SUPORTE ──
    cat_support = await guild.create_category("┣━━ 🎫 SUPORTE ━━┫")
    support_ow = pub_ow()
    ch_tickets = await guild.create_text_channel("「🎫」tickets", category=cat_support, overwrites=support_ow)

    # ── CATEGORIA: LOGS ──
    cat_logs = await guild.create_category("┗━━ 📋 LOGS ━━┛")
    logs_ow = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member_role: discord.PermissionOverwrite(read_messages=False),
        support_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
        owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    await guild.create_text_channel("「📋」logs-tickets", category=cat_logs, overwrites=logs_ow)
    await guild.create_text_channel("「🔍」logs-gerais", category=cat_logs, overwrites=logs_ow)

    # ── CONTEÚDO DOS CANAIS INFORMATIVOS ──

    # Convite
    invite = await ch_invites.create_invite(max_age=0, max_uses=0)
    embed_inv = discord.Embed(
        title="🔗 Convide seus amigos!",
        description=f"**Link do servidor:**\n```{invite.url}```\nCompartilhe e ajude nossa comunidade a crescer! 💜",
        color=0x5865F2
    )
    await ch_invites.send(embed=embed_inv)

    # Membros (será atualizado manualmente ou via evento)
    embed_mem = discord.Embed(
        title=f"👥 {guild.member_count} Membros",
        description="A contagem de membros é atualizada a cada novo membro que entrar!",
        color=0x43b581
    )
    await ch_members.send(embed=embed_mem)

    # Tutorial Key
    embed_tut = discord.Embed(
        title="📖 Tutorial — Como Gerar sua Key",
        description=(
            "**Passo 1:** Vá até o canal `「⚡」bot-cmds`\n"
            "**Passo 2:** Use o comando `/gerar_key`\n"
            "**Passo 3:** Copie a key gerada e guarde em um lugar seguro\n"
            "**Passo 4:** Use a key para acessar os recursos exclusivos\n\n"
            "⚠️ Cada usuário pode gerar apenas **1 key** por conta.\n"
            "📩 Em caso de dúvidas, abra um ticket no canal `「🎫」tickets`"
        ),
        color=0x7289da
    )
    embed_tut.set_footer(text=f"{guild.name} — Sistema de Keys")
    await ch_tutorial.send(embed=embed_tut)

    # Hits
    embed_hits = discord.Embed(
        title="🏆 Hall of Fame — Hits",
        description="Aqui ficam registrados os maiores hits e conquistas dos nossos membros!\n\nUse `/hit` para registrar o seu! 🎯",
        color=0xffd700
    )
    await ch_hits.send(embed=embed_hits)

    # Criar Log
    embed_log_user = discord.Embed(
        title="📝 Crie sua Log",
        description="Registre suas atividades e conquistas aqui!\nDigite livremente para criar sua log pessoal. 🗒️",
        color=0x99aab5
    )
    await ch_logs_user.send(embed=embed_log_user)

    # ── PAINEL DE TICKETS ──
    embed_ticket = discord.Embed(
        title="🎫 Central de Suporte",
        description=(
            "Bem-vindo à Central de Suporte!\n\n"
            "Clique em um dos botões abaixo para abrir um atendimento:\n\n"
            "🟢 **Abrir Ticket** — Fale com a equipe\n"
            "🤝 **Parceria** — Proposta de parceria\n"
            "❓ **Dúvidas** — Tire suas dúvidas\n"
            "💳 **Pagamento** — Formas de pagamento\n"
            "📝 **Criar Log** — Crie sua log pessoal\n\n"
            "⏰ Atendimento **24/7** • Resposta em até 12h"
        ),
        color=0x5865F2
    )
    embed_ticket.set_footer(text=f"{guild.name} — Suporte 24/7")
    if guild.icon:
        embed_ticket.set_thumbnail(url=guild.icon.url)

    view_ticket = TicketPanelView()
    await ch_tickets.send(embed=embed_ticket, view=view_ticket)

    await interaction.followup.send(
        "✅ **Servidor configurado com sucesso!**\n"
        "Categorias, canais, cargos e painéis foram criados!\n"
        "Use `/suport_cargo` e `/add_usuario` para gerenciar sua equipe. 🎉",
        ephemeral=True
    )

# ============================================================
# VIEWS — PAINEL DE TICKETS
# ============================================================
class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Abrir Ticket", emoji="🟢", style=discord.ButtonStyle.green, custom_id="ticket_open")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket(interaction, "ticket")

    @discord.ui.button(label="Parceria", emoji="🤝", style=discord.ButtonStyle.blurple, custom_id="ticket_parceria")
    async def parceria(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket(interaction, "parceria")

    @discord.ui.button(label="Dúvidas", emoji="❓", style=discord.ButtonStyle.secondary, custom_id="ticket_duvidas")
    async def duvidas(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket(interaction, "duvidas")

    @discord.ui.button(label="Pagamento", emoji="💳", style=discord.ButtonStyle.secondary, custom_id="ticket_pagamento")
    async def pagamento(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket(interaction, "pagamento")

    @discord.ui.button(label="Criar Log", emoji="📝", style=discord.ButtonStyle.secondary, custom_id="ticket_log")
    async def criar_log(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket(interaction, "criar-log")

async def create_ticket(interaction: discord.Interaction, tipo: str):
    guild = interaction.guild
    user = interaction.user
    gd = get_gd(guild.id)

    # Verificar se já tem ticket aberto
    for ch_id, tinfo in gd["tickets"].items():
        if tinfo.get("opener_id") == user.id:
            await interaction.response.send_message("❌ Você já possui um ticket aberto!", ephemeral=True)
            return

    support_role = guild.get_role(gd.get("support_role_id")) if gd.get("support_role_id") else None
    owner_role = discord.utils.get(guild.roles, name="👑 Owner")

    # Criar categoria para o ticket
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True),
        guild.owner: discord.PermissionOverwrite(read_messages=True, send_messages=True) if guild.owner else None,
    }
    if guild.owner:
        overwrites[guild.owner] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    if support_role:
        overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    if owner_role:
        overwrites[owner_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    # Remover None values
    overwrites = {k: v for k, v in overwrites.items() if v is not None}

    # Tentar criar dentro de uma categoria de suporte
    cat_support = discord.utils.get(guild.categories, name="┣━━ 🎫 SUPORTE ━━┫")
    ticket_name = f"ticket-{tipo}-{user.name[:10]}".lower().replace(" ", "-")

    try:
        ticket_ch = await guild.create_text_channel(
            ticket_name,
            category=cat_support,
            overwrites=overwrites
        )
    except Exception as e:
        await interaction.response.send_message(f"❌ Erro ao criar ticket: {e}", ephemeral=True)
        return

    # Registrar ticket
    gd["tickets"][ticket_ch.id] = {
        "opener_id": user.id,
        "tipo": tipo,
        "assumed": False,
        "opened_at": datetime.datetime.utcnow(),
        "warned_12h": False,
        "auto_closing": False
    }

    await interaction.response.send_message(f"✅ Ticket criado! {ticket_ch.mention}", ephemeral=True)

    # Mensagem inicial no ticket
    embed = discord.Embed(
        title=f"🎫 Ticket — {tipo.capitalize()}",
        description=(
            f"Olá {user.mention}! Seu ticket foi aberto com sucesso.\n\n"
            f"**Tipo:** {tipo}\n"
            f"**Aberto em:** <t:{int(datetime.datetime.utcnow().timestamp())}:F>\n\n"
            "A equipe de suporte será notificada em breve.\n"
            "Use o painel abaixo para interagir."
        ),
        color=0x43b581,
        timestamp=datetime.datetime.utcnow()
    )
    embed.set_footer(text="Atendimento 24/7")

    # Painel do membro
    member_view = MemberTicketView(user.id)
    await ticket_ch.send(content=f"{user.mention}", embed=embed, view=member_view)

    # Painel do admin (visível para support/owner)
    admin_view = AdminTicketView(user.id)
    embed_admin = discord.Embed(
        title="🛡️ Painel Admin/Support",
        description="Painel exclusivo para a equipe de suporte.",
        color=0x5865F2
    )
    await ticket_ch.send(embed=embed_admin, view=admin_view)

    # Notificar owner/support via DM
    notif_embed = discord.Embed(
        title="🔔 Novo Ticket Aberto!",
        description=f"**Usuário:** {user.mention} (`{user}`)\n**Tipo:** {tipo}\n**Canal:** {ticket_ch.mention}",
        color=0xffa500,
        timestamp=datetime.datetime.utcnow()
    )
    if guild.owner:
        try:
            await guild.owner.send(embed=notif_embed)
        except Exception:
            pass
    if support_role:
        for m in support_role.members:
            if m != guild.owner:
                try:
                    await m.send(embed=notif_embed)
                except Exception:
                    pass

# ── View do Membro no Ticket ──
class MemberTicketView(discord.ui.View):
    def __init__(self, opener_id: int):
        super().__init__(timeout=None)
        self.opener_id = opener_id

    async def check_perm(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.opener_id:
            await interaction.response.send_message("❌ Apenas quem abriu o ticket pode usar este painel.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Chamar Admin/Support", emoji="📣", style=discord.ButtonStyle.blurple, custom_id="member_call_admin")
    async def call_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_perm(interaction):
            return
        guild = interaction.guild
        gd = get_gd(guild.id)
        support_role = guild.get_role(gd.get("support_role_id")) if gd.get("support_role_id") else None
        embed = discord.Embed(
            title="📣 Membro Chamando Suporte!",
            description=f"{interaction.user.mention} está aguardando atendimento neste ticket.",
            color=0xffa500
        )
        await interaction.channel.send(embed=embed)
        # DM para owner e support
        notif = discord.Embed(
            title="🔔 Membro Chamando!",
            description=f"{interaction.user.mention} chamou suporte no ticket {interaction.channel.mention}",
            color=0xffa500
        )
        if guild.owner:
            try: await guild.owner.send(embed=notif)
            except: pass
        if support_role:
            for m in support_role.members:
                try: await m.send(embed=notif)
                except: pass
        await interaction.response.send_message("✅ Suporte notificado!", ephemeral=True)

    @discord.ui.button(label="Cancelar Ticket", emoji="❌", style=discord.ButtonStyle.red, custom_id="member_cancel_ticket")
    async def cancel_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_perm(interaction):
            return
        gd = get_gd(interaction.guild.id)
        tinfo = gd["tickets"].get(interaction.channel.id, {})
        await interaction.response.send_message("⚠️ Ticket será cancelado em **6 segundos**...", ephemeral=False)
        await asyncio.sleep(6)
        await _close_ticket_channel(interaction.guild, interaction.channel, tinfo, f"Cancelado pelo membro {interaction.user}")
        gd["tickets"].pop(interaction.channel.id, None)

# ── View do Admin/Support no Ticket ──
class AdminTicketView(discord.ui.View):
    def __init__(self, opener_id: int):
        super().__init__(timeout=None)
        self.opener_id = opener_id

    async def check_admin(self, interaction: discord.Interaction) -> bool:
        guild = interaction.guild
        gd = get_gd(guild.id)
        support_role = guild.get_role(gd.get("support_role_id")) if gd.get("support_role_id") else None
        is_owner = interaction.user.id == guild.owner_id
        is_support = support_role in interaction.user.roles if support_role else False
        has_owner_role = discord.utils.get(interaction.user.roles, name="👑 Owner") is not None
        if not (is_owner or is_support or has_owner_role):
            await interaction.response.send_message("❌ Apenas admins/support podem usar este painel.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Assumir Ticket", emoji="✅", style=discord.ButtonStyle.green, custom_id="admin_assume")
    async def assume(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_admin(interaction):
            return
        gd = get_gd(interaction.guild.id)
        tinfo = gd["tickets"].get(interaction.channel.id)
        if not tinfo:
            await interaction.response.send_message("❌ Ticket não encontrado.", ephemeral=True)
            return
        tinfo["assumed"] = True
        tinfo["assumed_by"] = interaction.user.id
        embed = discord.Embed(
            title="✅ Ticket Assumido",
            description=f"{interaction.user.mention} assumiu este ticket e está atendendo.",
            color=0x43b581
        )
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("✅ Você assumiu o ticket!", ephemeral=True)

    @discord.ui.button(label="Chamar Membro", emoji="📢", style=discord.ButtonStyle.blurple, custom_id="admin_call_member")
    async def call_member(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_admin(interaction):
            return
        opener = interaction.guild.get_member(self.opener_id)
        embed = discord.Embed(
            title="📢 Admin/Support Chamando!",
            description=f"{opener.mention}, o admin **{interaction.user.display_name}** está chamando você neste ticket!\nPor favor, responda o mais rápido possível.",
            color=0x5865F2
        )
        await interaction.channel.send(content=f"{opener.mention if opener else ''}", embed=embed)
        if opener:
            try:
                dm_embed = discord.Embed(
                    title="📢 Você foi chamado!",
                    description=f"O admin **{interaction.user.display_name}** está chamando você no ticket {interaction.channel.mention}",
                    color=0x5865F2
                )
                await opener.send(embed=dm_embed)
            except Exception:
                pass
        await interaction.response.send_message("✅ Membro notificado!", ephemeral=True)

    @discord.ui.button(label="Fechar Ticket", emoji="🔒", style=discord.ButtonStyle.red, custom_id="admin_close")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_admin(interaction):
            return
        gd = get_gd(interaction.guild.id)
        tinfo = gd["tickets"].get(interaction.channel.id, {})
        await interaction.response.send_message("🔒 Ticket fechando em **6 segundos**...", ephemeral=False)
        await asyncio.sleep(6)
        await _close_ticket_channel(interaction.guild, interaction.channel, tinfo, f"Fechado pelo admin {interaction.user}")
        gd["tickets"].pop(interaction.channel.id, None)

# ============================================================
# COMANDOS SLASH DE GERENCIAMENTO
# ============================================================
@tree.command(name="suport_cargo", description="Define o cargo de suporte (apenas dono)")
@app_commands.describe(cargo="Cargo que receberá permissões de suporte")
async def suport_cargo(interaction: discord.Interaction, cargo: discord.Role):
    if interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("❌ Apenas o **dono** pode usar este comando!", ephemeral=True)
        return
    gd = get_gd(interaction.guild.id)
    gd["support_role_id"] = cargo.id
    # Ajustar permissões do cargo
    await cargo.edit(permissions=discord.Permissions(
        read_messages=True, send_messages=True, manage_channels=True,
        read_message_history=True, attach_files=True, embed_links=True,
        manage_messages=True, use_application_commands=True
    ))
    embed = discord.Embed(
        title="✅ Cargo de Suporte Definido",
        description=f"O cargo {cargo.mention} agora é a equipe de suporte!",
        color=0x43b581
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="add_usuario", description="Adiciona um usuário à equipe de suporte (apenas dono)")
@app_commands.describe(usuario="Usuário a adicionar")
async def add_usuario(interaction: discord.Interaction, usuario: discord.Member):
    if interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("❌ Apenas o **dono** pode usar este comando!", ephemeral=True)
        return
    gd = get_gd(interaction.guild.id)
    support_role = interaction.guild.get_role(gd.get("support_role_id")) if gd.get("support_role_id") else None
    if not support_role:
        await interaction.response.send_message("❌ Defina primeiro o cargo de suporte com `/suport_cargo`!", ephemeral=True)
        return
    await usuario.add_roles(support_role)
    if usuario.id not in gd["support_users"]:
        gd["support_users"].append(usuario.id)
    embed = discord.Embed(
        title="✅ Usuário Adicionado ao Suporte",
        description=f"{usuario.mention} agora faz parte da equipe de suporte!",
        color=0x43b581
    )
    await interaction.response.send_message(embed=embed)
    try:
        await usuario.send(embed=discord.Embed(
            title="🎉 Bem-vindo ao Suporte!",
            description=f"Você foi adicionado à equipe de suporte de **{interaction.guild.name}**!",
            color=0x43b581
        ))
    except Exception:
        pass

@tree.command(name="delet_user", description="Remove um usuário da equipe de suporte (apenas dono)")
@app_commands.describe(usuario="Usuário a remover")
async def delet_user(interaction: discord.Interaction, usuario: discord.Member):
    if interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("❌ Apenas o **dono** pode usar este comando!", ephemeral=True)
        return
    gd = get_gd(interaction.guild.id)
    support_role = interaction.guild.get_role(gd.get("support_role_id")) if gd.get("support_role_id") else None
    if support_role and support_role in usuario.roles:
        await usuario.remove_roles(support_role)
    if usuario.id in gd["support_users"]:
        gd["support_users"].remove(usuario.id)
    embed = discord.Embed(
        title="✅ Usuário Removido do Suporte",
        description=f"{usuario.mention} foi removido da equipe de suporte.",
        color=0xf04747
    )
    await interaction.response.send_message(embed=embed)

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    # Iniciar Flask em thread separada
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("🌐 Painel Web rodando em http://0.0.0.0:8080")

    # Rodar bot
    bot.run(TOKEN)
