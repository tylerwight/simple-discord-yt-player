import os
import asyncio
import logging
import random

import discord
from discord import app_commands
from dotenv import load_dotenv

import downloader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(threadName)s] %(name)s: %(message)s",
)

dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(dotenv_path)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# Global
queue: list[dict] = []
now_playing: str | None = None
goto_next: bool = False
downloading: bool = False

player_task: asyncio.Task | None = None
queue_lock = asyncio.Lock()          # only for short queue mutations
player_wakeup = asyncio.Event()      # wake the player when new stuff is queued



@bot.event
async def on_ready():
    my_guild = 205936996139401218
    logging.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await tree.sync()
        logging.info(f"Synced {len(synced)} slash commands globally")
    except Exception as e:
        logging.exception(f"Failed to sync commands: {e}")


def _is_youtube_url(url: str) -> bool:
    return ("youtube.com" in url) or ("youtu.be" in url)


async def _ensure_voice(interaction: discord.Interaction) -> discord.VoiceClient | None:
    if not interaction.user:
        await interaction.followup.send("Could not resolve your member info.", ephemeral=True)
        return None

    if not interaction.user.voice:
        await interaction.followup.send("You are not connected to a voice channel.", ephemeral=True)
        return None

    if interaction.guild is None:
        await interaction.response.send_message("This command only works in a server.", ephemeral=True)
        return None

    voice_client = interaction.guild.voice_client
    if not voice_client:
        channel = interaction.user.voice.channel
        voice_client = await channel.connect()

    return voice_client





async def player_loop(guild_id: int):
    """
    Background task that plays songs until the queue is empty, then disconnects.
    """
    global queue, now_playing, downloading, goto_next, player_task

    logging.info("Player loop started.")

    try:
        while True:
            
            while True:
                async with queue_lock:
                    has_items = len(queue) > 0
                if has_items:
                    break
                player_wakeup.clear()
                await player_wakeup.wait()

            async with queue_lock:
                if not queue:
                    continue
                current_song = queue.pop(0)

            now_playing = current_song.get("title")
            logging.info(f"Now playing: {now_playing} ({current_song.get('type')})")

            guild = bot.get_guild(guild_id)
            if guild is None:
                logging.warning("Guild not found; stopping player loop.")
                break

            voice_client = guild.voice_client
            if voice_client is None:
                logging.warning("No voice client; stopping player loop.")
                break

            # Download song
            if current_song["type"] == "Youtube":
                try:
                    voice_client.play(discord.FFmpegPCMAudio("dlsong.mp3"))
                except Exception as e:
                    logging.warning(f"Download notification sound failed: {e}")

                downloading = True
                try:
                    song_filename = await asyncio.to_thread(downloader.get_song, current_song["url"], max_length=100 * 60)
                except Exception as e:
                    logging.warning(f"Error downloading song: {e}")
                    downloading = False
                    now_playing = None
                    continue
                downloading = False

            elif current_song["type"] == "Local":
                song_filename = current_song["url"]
            else:
                logging.warning(f"Unknown queue type: {current_song.get('type')}")
                now_playing = None
                continue

            try:
                voice_client.play(discord.FFmpegPCMAudio(song_filename))
            except Exception as e:
                logging.warning(f"Failed to start playback: {e}")
                now_playing = None
                continue

            while voice_client.is_playing():
                await asyncio.sleep(0.5)
                if goto_next:
                    goto_next = False
                    voice_client.stop()
                    break

            now_playing = None

            async with queue_lock:
                empty = len(queue) == 0

            if empty:
                try:
                    await voice_client.disconnect()
                except Exception:
                    pass
                break

    finally:
        player_task = None
        now_playing = None
        downloading = False
        goto_next = False
        logging.info("Player loop ended.")


def ensure_player_started(guild_id: int):
    global player_task
    if player_task is None or player_task.done():
        player_task = asyncio.create_task(player_loop(guild_id))





@tree.command(name="play", description="Play a YouTube URL or an attached .mp3 file.")
@app_commands.describe(url="YouTube URL (youtube.com / youtu.be)", file="Attach an .mp3 file to play locally")
async def play(interaction: discord.Interaction, url: str | None = None, file: discord.Attachment | None = None):
    global queue
    await interaction.response.defer(thinking=True)


    if (url is None) and (file is None):
        await interaction.followup.send(
            "Please provide either a YouTube URL (url=...) or attach an .mp3 (file=...).",
            ephemeral=True,
        )
        return

    if (url is not None) and (file is not None):
        await interaction.followup.send("You attached a file AND sent a URL. Pick one buddy.", ephemeral=True)
        return

    if url is not None and not _is_youtube_url(url):
        await interaction.followup.send("Please use a YouTube URL (youtube.com / youtu.be).", ephemeral=True)
        return

    voice_client = await _ensure_voice(interaction)
    if voice_client is None:
        return



    # Add to queue and play if not playing
    async with queue_lock:
        if url is not None:
            try:
                tmp_title = await downloader.get_title(url)
            except Exception as e:
                await interaction.followup.send(f"Error reading YouTube title: {e}", ephemeral=True)
                return

            queue.append({"type": "Youtube", "title": tmp_title, "url": url})
            await send_update_embed(interaction, f"Queued Song", f"[{tmp_title}]({url})", 5)

        elif file is not None:
            filename_lower = (file.filename or "").lower()
            if not filename_lower.endswith(".mp3"):
                await interaction.followup.send("Please upload an **.mp3** file.", ephemeral=True)
                return

            os.makedirs("local_uploads", exist_ok=True)
            local_path = os.path.join("local_uploads", file.filename)

            try:
                await file.save(local_path)
            except Exception as e:
                await interaction.followup.send(f"Failed to download attachment: `{e}`", ephemeral=True)
                return

            queue.append({"type": "Local", "title": filename_lower, "url": local_path})
            await send_update_embed(interaction, f"Queued Song", f"{filename_lower}", 5)

    ensure_player_started(interaction.guild.id)
    player_wakeup.set()


@tree.command(name="playlist", description="Add a YouTube playlist to the queue.")
@app_commands.describe(url="YouTube playlist URL")
async def playlist(interaction: discord.Interaction, url: str):
    await interaction.response.defer(thinking=True)

    try:
        entries = await downloader.get_playlist_entries(url)
    except Exception as e:
        await interaction.followup.send(f"Error reading playlist: {e}", ephemeral=True)
        return

    if not entries:
        await interaction.followup.send("No playable entries found in that playlist.", ephemeral=True)
        return

    async with queue_lock:
        for item in entries:
            queue.append({"type": "Youtube", "title": item["title"], "url": item["url"]})
        added = len(entries)

    voice_client = await _ensure_voice(interaction)
    if voice_client is None:
        return
    
    ensure_player_started(interaction.guild.id)
    player_wakeup.set()

    await send_update_embed(interaction, "Added playlist to the queue", f"Added **{added}** songs to the queue!", 5)


@tree.command(name="skip", description="Skip the current song.")
async def skip(interaction: discord.Interaction):
    global goto_next

    if interaction.guild is None or interaction.guild.voice_client is None:
        await interaction.response.send_message("I'm not connected to a voice channel.", ephemeral=True)
        return

    goto_next = True
    await send_update_embed(interaction, "Skipping Song", "", 5)


@tree.command(name="stop", description="Stop playback, clear the queue, and disconnect.")
async def stop(interaction: discord.Interaction):
    global queue, now_playing, goto_next, downloading

    if interaction.guild is None:
        await interaction.response.send_message("This command only works in a server.", ephemeral=True)
        return

    vc = interaction.guild.voice_client
    async with queue_lock:
        queue.clear()
        now_playing = None
        goto_next = False
        downloading = False

    if vc:
        if vc.is_playing():
            vc.stop()
        try:
            await vc.disconnect()
        except Exception:
            pass

    await interaction.response.send_message("Stopped playing and disconnected.")


@tree.command(name="queue", description="Show the current queue.")
async def show_queue(interaction: discord.Interaction):
    await send_update_embed(interaction, "Current Queue", "", 10)


@tree.command(name="shuffle", description="Shuffle the current queue.")
async def shuffle(interaction: discord.Interaction):
    async with queue_lock:
        if not queue:
            await send_update_embed(interaction, "Queue is Empty", "", 5)
            return
        random.shuffle(queue)

    await send_update_embed(interaction, "Queue Shuffled", "", 5)


async def send_update_embed(interaction: discord.Interaction, intitle: str, message: str, length: int = 10, chunk_size: int = 5, ephemeral: bool = False,):
    global queue, now_playing

    embed = discord.Embed(
        title=intitle,
        description=message,
        color=discord.Color.blurple(),
    )

    embed.add_field(
        name="▶️ Currently Playing",
        value=f"**{now_playing}**" if now_playing else "Nothing",
        inline=False,
    )

    if not queue:
        embed.add_field(name="📜 Up Next", value="Queue is empty.", inline=False)
        embed.set_footer(text="Total tracks in queue: 0")
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
        return

    shown = queue[:length]

    lines = []
    for i, item in enumerate(shown, start=1):
        title = item.get("title", "Unknown title")
        qtype = item.get("type", "Unknown")
        url = item.get("url")

        if len(title) > 80:
            title = title[:77] + "..."

        if qtype == "Youtube" and url:
            line = f"`{i}.` **[{title}]({url})**  •  *{qtype}*"
        else:
            line = f"`{i}.` **{title}**  •  *{qtype}*"

        lines.append(line)

    def add_up_next_fields(embed_obj: discord.Embed, lines_list: list[str], chunk: int):
        field_idx = 0
        i = 0
        while i < len(lines_list):
            field_idx += 1
            field_lines = []
            field_len = 0
            count_in_field = 0

            while i < len(lines_list) and count_in_field < chunk:
                candidate = lines_list[i]
                candidate_len = len(candidate) + (1 if field_lines else 0)
                if field_len + candidate_len > 1024:
                    break
                field_lines.append(candidate)
                field_len += candidate_len
                count_in_field += 1
                i += 1

            if not field_lines and i < len(lines_list):
                field_lines = [lines_list[i][:1000] + "…"]
                i += 1

            name = "📜 Up Next" if field_idx == 1 else "\u200b"
            embed_obj.add_field(name=name, value="\n".join(field_lines), inline=False)

    add_up_next_fields(embed, lines, chunk_size)

    if len(queue) > length:
        embed.add_field(
            name="\u200b",
            value=f"… and **{len(queue) - length}** more in queue.",
            inline=False,
        )

    embed.set_footer(text=f"Total tracks in queue: {len(queue)}")
    if interaction.response.is_done():
        await interaction.followup.send(embed=embed, ephemeral=ephemeral)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)


bot.run(DISCORD_TOKEN)
