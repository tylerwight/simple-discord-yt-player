import discord
from discord.ext import commands
import asyncio
from dotenv import load_dotenv
import os
import downloader
import logging
import random

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(threadName)s] %(name)s: %(message)s",
)

dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(dotenv_path)
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)
queue = []
now_playing = None
goto_next = False
downloading = False

@bot.command(help="Plays a youtube URL or attached mp3 file: `!play >youtube URL<` or `!play` w/ mp3 file attached")
async def play(ctx, url: str = None):
    global downloading 
    global now_playing
    
    if not ctx.author.voice:
        await ctx.send("You are not connected to a voice channel.")
        return
    
    if (url is None) and (not ctx.message.attachments):
         await ctx.send("Please add a youtube URL or attach an mp3 file: `!play youtube.com/abcxyz`")
         return

    if (not ctx.message.attachments) and not ("youtube.com" in url or "youtu.be" in url):
        await ctx.send("Please use a youtube URL")
        return

    if ctx.message.attachments and url is not None:
        await ctx.send("You attached a file AND sent a URL. Pick one buddy")
        return
    
    voice_client = ctx.voice_client
    if not voice_client:
        channel = ctx.author.voice.channel
        voice_client = await channel.connect()


    if url is not None:
        try:
            tmp_title = await downloader.get_title(url)
            queue.append({"type": "Youtube", "title": tmp_title, "url": url})

            if voice_client.is_playing() or downloading == True:
                await send_update_embed(ctx, f"Added {tmp_title} to queue.", "", 5)
                return
            else:
                await send_update_embed(ctx, f"Playing {tmp_title}", "", 5)
            
        except Exception as e:
            await ctx.send (f"Error adding Youtube song to queue: {e}")
            return

    if ctx.message.attachments:
        try:
            for attachment in ctx.message.attachments:

                filename_lower = (attachment.filename or "").lower()
                if not filename_lower.endswith(".mp3"):
                    await ctx.send("Please upload an **.mp3** file.")
                    return
                
                os.makedirs("local_uploads", exist_ok=True)
                local_path = os.path.join("local_uploads", attachment.filename)

                try:
                    await attachment.save(local_path)
                except Exception as e:
                    await ctx.send(f"Failed to download attachment: `{e}`")
                    return
                
                queue.append({"type": "Local", "title": filename_lower, "url": local_path})

                if voice_client.is_playing() or downloading == True:
                    await send_update_embed(ctx, f"Added {filename_lower} to queue.", "", 5)
                else:
                    await send_update_embed(ctx, f"Playing {filename_lower}", "", 5)

        except Exception as e:
            await ctx.send(f"Error adding local file song to queue {e}")
            return
        
        if voice_client.is_playing() or downloading == True:
                return
            

    #Loop while there is a queue
    while len(queue) > 0:
        current_song = queue.pop(0)
        
        now_playing = current_song["title"]
        logging.info(f"Playing song{now_playing}")
        await asyncio.sleep(1)

        #play an audio clip to confirm to user we're downloading the song
        if current_song["type"] == "Youtube":

            dl_notif_source = discord.FFmpegPCMAudio('dlsong.mp3')
            voice_client.play(dl_notif_source)
            
            #download the song, handle errors
            downloading = True
            try:
                song_filename = await asyncio.to_thread(downloader.get_song, current_song["url"], max_length = 100 * 60)
            except Exception as e:
                logging.warning(f"Error downloading song: {e}")
                await ctx.send(f"Error downloading song: {e}")
                downloading = False
                continue

            downloading = False
    
        if current_song["type"] == "Local":
            song_filename = current_song["url"]
            await asyncio.sleep(1)

        audio_source = discord.FFmpegPCMAudio(song_filename)
        voice_client.play(audio_source)

        while voice_client.is_playing():
                await asyncio.sleep(2)
                global goto_next
                if goto_next == True:
                    voice_client.stop()
                    goto_next = False
                    break



    now_playing = None
    await voice_client.disconnect()


@bot.command(help="Adds playlist to queue. Usage: !playlist <playlist_url>")
async def playlist(ctx, url: str = None):
    if not url:
        await ctx.send("Please provide a YouTube playlist URL. Example: `!play_playlist https://www.youtube.com/...`")
        return

    try:
        entries = await downloader.get_playlist_entries(url)
    except Exception as e:
        await ctx.send(f"Error reading playlist: {e}")
        return

    if not entries:
        await ctx.send("No playable entries found in that playlist.")
        return

    added = 0
    for item in entries:
        queue.append({"type": "Youtube", "title": item["title"], "url": item["url"]})
        added += 1

    await send_update_embed(ctx, "Added to queue",  f"Added **{added}** songs to the queue!", 5)




@bot.command(help="Skips current song")
async def skip(ctx):
    if ctx.voice_client is None:
        await ctx.send("I'm not connected to a voice channel.")
        return
    
    
    global goto_next
    goto_next = True
    await send_update_embed(ctx, f"Skipping Song", "", 5)
    


@bot.command(help="Stops all audio and disconnects the bot, also clears the queue.")
async def stop(ctx):
    if ctx.voice_client is None:
        await ctx.send("I'm not connected to a voice channel.")
        return

    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()

    await ctx.voice_client.disconnect()
    await ctx.send("Stopped playing and disconnected.")
    global queue
    queue = []
    global now_playing
    now_playing = None



@bot.command(help="Shows the current queue.")
async def show_queue(ctx):
    await send_update_embed(ctx, "Current Queue", "", 10)
    


@bot.command(help="Shuffles the current queue.")
async def shuffle(ctx):
    global queue

    if not queue:
        await send_update_embed(ctx, "Queue is Empty", "", 5)
        return

    random.shuffle(queue)
    await send_update_embed(ctx, "Queue Shuffled", "", 5)


async def send_update_embed(ctx, intitle: str, message: str, length: int = 10, chunk_size: int = 5):
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
        await ctx.send(embed=embed)
        return

    shown = queue[:length]

    # Build formatted lines first
    lines = []
    for i, item in enumerate(shown, start=1):
        title = item.get("title", "Unknown title")
        qtype = item.get("type", "Unknown")
        url = item.get("url")

        # (Optional) hard-trim absurd titles so one song doesn't eat the whole field
        if len(title) > 80:
            title = title[:77] + "..."

        if qtype == "Youtube" and url:
            line = f"`{i}.` **[{title}]({url})**  •  *{qtype}*"
        else:
            line = f"`{i}.` **{title}**  •  *{qtype}*"

        lines.append(line)

    # Split into multiple fields, trying for chunk_size songs per field,
    # BUT also respecting the 1024 char field limit.
    def add_up_next_fields(embed: discord.Embed, lines: list[str], chunk_size: int):
        field_idx = 0
        i = 0

        while i < len(lines):
            field_idx += 1
            field_lines = []
            field_len = 0
            count_in_field = 0

            while i < len(lines) and count_in_field < chunk_size:
                candidate = lines[i]
                candidate_len = len(candidate) + (1 if field_lines else 0)  # + newline if needed

                # If adding this line would exceed Discord's 1024 limit, stop this field early.
                if field_len + candidate_len > 1024:
                    break

                field_lines.append(candidate)
                field_len += candidate_len
                count_in_field += 1
                i += 1

            # If we couldn't even fit a single line (super long URL/title), truncate brutally.
            if not field_lines and i < len(lines):
                truncated = lines[i][:1000] + "…"
                field_lines = [truncated]
                i += 1

            name = "📜 Up Next" if field_idx == 1 else "\u200b"  # blank header for subsequent fields
            embed.add_field(name=name, value="\n".join(field_lines), inline=False)

    add_up_next_fields(embed, lines, chunk_size)

    if len(queue) > length:
        embed.add_field(
            name="\u200b",
            value=f"… and **{len(queue) - length}** more in queue.",
            inline=False,
        )

    embed.set_footer(text=f"Total tracks in queue: {len(queue)}")
    await ctx.send(embed=embed)



bot.run(DISCORD_TOKEN)