import discord
from discord.ext import commands
import asyncio
from dotenv import load_dotenv
import os
import downloader
import logging

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

@bot.command(help="!play >youtube URL< -- Plays a Youtube Video's audio in the voice channel, or adds it to the queue.")
async def play(ctx, url: str = None):
    global downloading 
    global now_playing
    
    if not ctx.author.voice:
        await ctx.send("You are not connected to a voice channel.")
        return
    
    if url is None:
         await ctx.send("Please put a URL after play command. EX: '!play youtube.com/abcxyz'")
         return

    if not ("youtube.com" in url or "youtu.be" in url):
        await ctx.send("Please use a youtube URL")
        return

    
    
    voice_client = ctx.voice_client
    if not voice_client:
        channel = ctx.author.voice.channel
        voice_client = await channel.connect()

    #queue.append(url)
    try:
        tmp_title = downloader.get_title(url)
        queue.append({"type": "Youtube", "title": tmp_title, "url": url})


        if voice_client.is_playing() or downloading == True:
            await ctx.send(f"Added {tmp_title} to queue.")
            return
        
    except Exception as e:
        await ctx.send (f"Error adding song to queue: {e}")
        return


    #Loop while there is a queue
    while len(queue) > 0:
        current_song = queue.pop(0)
        
        now_playing = current_song["title"]
        logging.info(f"Playing song{now_playing}")
        await asyncio.sleep(1)

        #play an audio clip to confirm to user we're downloading the song
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
            return

        downloading = False
    


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


@bot.command(help="!play_local (attach an mp3) -- Immediately plays the attached mp3, interrupting current audio.")
async def play_local(ctx):
    if not ctx.author.voice:
        await ctx.send("You are not connected to a voice channel.")
        return

    if not ctx.message.attachments:
        await ctx.send("Please attach an mp3 file to the same message. Example: `!play_local` + attach file.")
        return

    attachment = ctx.message.attachments[0]

    filename_lower = (attachment.filename or "").lower()
    if not filename_lower.endswith(".mp3"):
        await ctx.send("Please upload an **.mp3** file.")
        return

    voice_client = ctx.voice_client
    if not voice_client:
        channel = ctx.author.voice.channel
        voice_client = await channel.connect()


    if voice_client.is_playing():
        voice_client.stop()

    os.makedirs("local_uploads", exist_ok=True)
    local_path = os.path.join("local_uploads", attachment.filename)

    try:
        await attachment.save(local_path)
    except Exception as e:
        await ctx.send(f"Failed to download attachment: `{e}`")
        return

    # Play the uploaded file
    try:
        audio_source = discord.FFmpegPCMAudio(local_path)
        voice_client.play(audio_source)
        await ctx.send(f"Playing uploaded file: **{attachment.filename}**")

    except Exception as e:
        await ctx.send(f"Failed to play that file: `{e}`")
        return

    while voice_client.is_playing():
        await asyncio.sleep(2)

    try:
        os.remove(local_path)
    except Exception:
        pass


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



@bot.command(help="Shows the current queue of YouTube links.")
async def show_queue(ctx):
    if ctx.voice_client is None:
        await ctx.send("I'm not connected to a voice channel.")
        return
    
    if queue:
        pretty_queue = "\n".join(
            f"#{i+1} Title: {queue_item['title']} -- Type: {queue_item['type']}"
            for i, queue_item in enumerate(queue)
        )
    else:
         pretty_queue = "Nothing in queue."


    await ctx.send(f"**__Currently Playing__**\n {now_playing}\n**__Queue__**\n {pretty_queue}")



@bot.command(help="Shows the current queue with more info")
async def show_queue_debug(ctx):
    if ctx.voice_client is None:
        await ctx.send("I'm not connected to a voice channel.")
        return
    
    if queue:
        pretty_queue = "\n".join(
            f"#{i+1} Title: {queue_item['title']} -- Type: {queue_item['type']} -- URL: <{queue_item['url']}>"
            for i, queue_item in enumerate(queue)
        )
    else:
         pretty_queue = "Nothing in queue."


    await ctx.send(f"**__Currently Playing__**\n {now_playing}\n**__Queue__**\n {pretty_queue}")



@bot.command(help="Skips current song")
async def skip(ctx):
    if ctx.voice_client is None:
        await ctx.send("I'm not connected to a voice channel.")
        return
    
    global goto_next
    goto_next = True


@bot.command(help="tests voice connection")
async def testvoice(ctx):
    if not ctx.author.voice:
        await ctx.send("You are not connected to a voice channel.")
        return

    voice_client = ctx.voice_client
    if not voice_client:
        channel = ctx.author.voice.channel
        voice_client = await channel.connect()

    dl_notif_source = discord.FFmpegPCMAudio('dlsong.mp3')
    voice_client.play(dl_notif_source)

    while voice_client.is_playing():
            await asyncio.sleep(2)
    
    await voice_client.disconnect()


bot.run(DISCORD_TOKEN)