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

    queue.append(url)

    if voice_client.is_playing() or downloading == True:
        await ctx.send(f"Added <{url}> to queue.")
        return

    #Loop while there is a queue
    while len(queue) > 0:
        current_url = queue.pop(0)
        
        now_playing = current_url
        logging.info(f"Playing song{current_url}")
        await asyncio.sleep(1)

        #play an audio clip to confirm we're downloading the song
        dl_notif_source = discord.FFmpegPCMAudio('dlsong.mp3')
        voice_client.play(dl_notif_source)
        
        #download the song, return the file name or error message
        
        downloading = True
        success, message = await asyncio.to_thread(downloader.get_song, current_url)
        downloading = False
        
        if not success:
                await ctx.send(message)


        audio_source = discord.FFmpegPCMAudio(message)
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



@bot.command(help="Shows the current queue of YouTube links.")
async def show_queue(ctx):
    if ctx.voice_client is None:
        await ctx.send("I'm not connected to a voice channel.")
        return
    
    if queue:
         pretty_queue = "\n".join(f"<{url}>" for url in queue)
    else:
         pretty_queue = "Nothing in queue."


    await ctx.send(f"**__Currently Playing__**\n <{now_playing}>\n**__Queue__**\n {pretty_queue}")


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