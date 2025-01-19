import discord
from discord.ui import Button, View
import requests
import matplotlib.pyplot as plt
import io
import asyncio

# Bot token és API beállítások
DISCORD_TOKEN = "bot token"
API_TOKEN = "client token"
PANEL_URL = "panel URL"

# Szerverek és csatornák listája
SERVERS = [
    {"server_id": "49bc3cac-a5cb-40cc-9b3d-f9ac0df9c637", "channel_id": 1330492346638536744},
    #{"server_id": "73d1c6f2-47ea-41fb-82d0-f7aa231cf3cd", "channel_id": 1330512248145449030},
    #{"server_id": "d33bb567-21ac-4399-95fc-26e12025bab9", "channel_id": 123456789012345678},
    #{"server_id": "abcd1234-efgh5678-ijkl9012-mnop3456qrst", "channel_id": 987654321098765432},
    #{"server_id": "d33bb567-21ac-4399-95fc-26e12025bab9", "channel_id": 123456789012345678},
    #{"server_id": "abcd1234-efgh5678-ijkl9012-mnop3456qrst", "channel_id": 987654321098765432},
    #{"server_id": "d33bb567-21ac-4399-95fc-26e12025bab9", "channel_id": 123456789012345678},
    #{"server_id": "abcd1234-efgh5678-ijkl9012-mnop3456qrst", "channel_id": 987654321098765432},
    #{"server_id": "d33bb567-21ac-4399-95fc-26e12025bab9", "channel_id": 123456789012345678},
    #{"server_id": "abcd1234-efgh5678-ijkl9012-mnop3456qrst", "channel_id": 987654321098765432},
    # A többi szervert légyszi itt adjatok hozzá a fentiek szerint.
]

# Intents beállítása
intents = discord.Intents.default()
intents.message_content = True

# Bot inicializálás
client = discord.Client(intents=intents)

# API hívás: Használati és limit adatok lekérdezése
def get_server_usage_and_limits(server_id):
    # Használati adatok lekérdezése
    usage_response = requests.get(
        f"{PANEL_URL}/api/client/servers/{server_id}/resources",
        headers={
            "Authorization": f"Bearer {API_TOKEN}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )

    # Konfigurációs adatok (limitek) lekérdezése
    config_response = requests.get(
        f"{PANEL_URL}/api/client/servers/{server_id}",
        headers={
            "Authorization": f"Bearer {API_TOKEN}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )

    if usage_response.status_code == 200 and config_response.status_code == 200:
        usage_data = usage_response.json()
        config_data = config_response.json()
        return {
            "usage": usage_data,
            "limits": config_data["attributes"]["limits"],
        }
    else:
        if usage_response.status_code != 200:
            print(f"Használati adat hiba [{server_id}]: {usage_response.status_code}, {usage_response.text}")
        if config_response.status_code != 200:
            print(f"Konfigurációs adat hiba [{server_id}]: {config_response.status_code}, {config_response.text}")
        return None

def control_server(server_id, action):
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    payload = {"signal": action}
    response = requests.post(f"{PANEL_URL}/api/client/servers/{server_id}/power", headers=headers, json=payload)
    
    if response.status_code == 204:  # A sikeres művelet HTTP státuszkódja
        print(f"Szerver {action} sikeresen végrehajtva.")
        return True
    else:
        print(f"Hiba a {action} művelet során: {response.status_code}, {response.text}")
        return False

# Grafikon készítése
def create_usage_graph(cpu_usage, cpu_max, memory_used_mib, memory_max_mib):
    plt.style.use("dark_background")
    plt.figure(figsize=(10, 6))

    ram_max = memory_max_mib if memory_max_mib and memory_max_mib > 0 else memory_used_mib + 50
    cpu_max_display = f"{cpu_max}%" if cpu_max and cpu_max > 0 else "Unlimited"
    ram_max_display = f"{memory_max_mib:.2f} MiB" if memory_max_mib else "Unlimited"

    bars = plt.bar(
        ["CPU (%)", "RAM (MiB)"],
        [cpu_usage, memory_used_mib],
        color=["#9b59b6", "#2ecc71"],
        alpha=0.9,
        edgecolor="white",
        linewidth=1.5
    )

    plt.text(
        0,
        cpu_usage + (5 if cpu_usage > 10 else 2),
        f"{cpu_usage:.2f}% / {cpu_max_display}",
        ha="center",
        fontsize=10,
        color="white"
    )
    plt.text(
        1,
        memory_used_mib + (5 if memory_used_mib > 500 else 2),
        f"{memory_used_mib:.2f} MiB / {ram_max_display}",
        ha="center",
        fontsize=10,
        color="white"
    )

    plt.title("Szerver Használati Adatok", fontsize=16, color="white", pad=20)
    plt.ylabel("Használati Értékek", fontsize=12, color="white")
    plt.ylim(0, max(cpu_usage + 50, ram_max))
    plt.xticks(fontsize=12, color="white")
    plt.yticks(fontsize=12, color="white")
    plt.grid(axis="y", linestyle="--", alpha=0.3, color="gray")
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format="png", bbox_inches="tight", dpi=100)
    buffer.seek(0)
    plt.close()
    return buffer

# Állapot frissítése
async def update_status_message(server_id, channel):
    message = None
    while True:
        data = get_server_usage_and_limits(server_id)
        if not data:
            print(f"Nem sikerült lekérdezni a {server_id} szerver adatait.")
            await asyncio.sleep(5)
            continue

        usage = data["usage"]["attributes"]["resources"]
        limits = data["limits"]

        cpu_usage = usage["cpu_absolute"]
        cpu_max = limits.get("cpu", None)
        memory_bytes = usage["memory_bytes"]
        memory_limit_mib = limits.get("memory", None)

        if memory_limit_mib and memory_limit_mib > 0:
            memory_max_gib = memory_limit_mib / 1024
        else:
            memory_max_gib = None

        cpu_max_display = f"{cpu_max}%" if cpu_max and cpu_max > 0 else "Unlimited"
        memory_used_mib = memory_bytes / 1024 / 1024
        memory_max_display = f"{memory_max_gib:.2f} GiB" if memory_max_gib else "Unlimited"

        state = data["usage"]["attributes"]["current_state"]

        graph = create_usage_graph(
            cpu_usage,
            cpu_max,
            memory_used_mib,
            memory_max_gib * 1024 if memory_max_gib else None
        )

        embed = discord.Embed(
            title=f"Szerver Állapot - {server_id}",
            description=f"A szerver jelenlegi állapota: **{state}**",
            color=discord.Color.green() if state == "running" else discord.Color.red(),
        )
        embed.add_field(name="CPU Használat", value=f"{cpu_usage:.2f}% / {cpu_max_display}", inline=True)
        embed.add_field(name="RAM Használat", value=f"{memory_used_mib:.2f} MiB / {memory_max_display}", inline=True)
        file = discord.File(graph, filename="usage.png")
        embed.set_image(url="attachment://usage.png")

        # Gombok létrehozása
        view = View()

        # Start gomb
        async def start_callback(interaction):
            if control_server(server_id, "start"):
                await interaction.response.send_message("A szerver indítása sikeres volt!", ephemeral=True)
            else:
                await interaction.response.send_message("Nem sikerült indítani a szervert!", ephemeral=True)

        start_button = Button(label="Start", style=discord.ButtonStyle.success, disabled=(state == "running"))
        start_button.callback = start_callback
        view.add_item(start_button)

        # Stop gomb
        async def stop_callback(interaction):
            if control_server(server_id, "stop"):
                await interaction.response.send_message("A szerver leállítása sikeres volt!", ephemeral=True)
            else:
                await interaction.response.send_message("Nem sikerült leállítani a szervert!", ephemeral=True)

        stop_button = Button(label="Stop", style=discord.ButtonStyle.danger, disabled=(state != "running"))
        stop_button.callback = stop_callback
        view.add_item(stop_button)

        # Restart gomb
        async def restart_callback(interaction):
            if control_server(server_id, "restart"):
                await interaction.response.send_message("A szerver újraindítása sikeres volt!", ephemeral=True)
            else:
                await interaction.response.send_message("Nem sikerült újraindítani a szervert!", ephemeral=True)

        restart_button = Button(label="Restart", style=discord.ButtonStyle.primary, disabled=(state != "running"))
        restart_button.callback = restart_callback
        view.add_item(restart_button)

        if message is None:
            message = await channel.send(embed=embed, file=file, view=view)
        else:
            await message.edit(embed=embed, attachments=[file], view=view)

        await asyncio.sleep(5)

@client.event
async def on_ready():
    print(f"Bejelentkezve: {client.user}")

    for server in SERVERS:
        channel = client.get_channel(server["channel_id"])
        if channel is None:
            print(f"Nem található a megadott csatorna ({server['channel_id']})!")
            continue

        asyncio.create_task(update_status_message(server["server_id"], channel))

client.run(DISCORD_TOKEN)