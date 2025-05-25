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


url = 'https://www.youtube.com/watch?v=xcEvNwQ7v-U'


intents = discord.Intents.default()
intents.message_content = True  # Required to read text commands

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.command()
async def play(ctx, url: str):
    if not ctx.author.voice:
        await ctx.send("You are not connected to a voice channel.")
        return
    
    if "youtube.com" not in url:
        await ctx.send("Please paste a youtube URL.")
        return
    
    voice_client = ctx.voice_client
    if not voice_client:
        channel = ctx.author.voice.channel
        voice_client = await channel.connect()

    if voice_client.is_playing():
        await ctx.send("I'm already playing something. Please wait until it's finished or use !stop.")
        return
    


    logging.info(f"downloading song from url {url}")
    await asyncio.sleep(1)

    dl_notif_source = discord.FFmpegPCMAudio('dlsong.mp3')
    voice_client.play(dl_notif_source)
    
    #success, message = downloader.get_song(url)
    success, message = await asyncio.to_thread(downloader.get_song, url)
    
    if not success:
        await ctx.send(message)


    # Play audio file
    audio_source = discord.FFmpegPCMAudio(message)
    voice_client.play(audio_source)

    # Wait for the audio to finish
    while voice_client.is_playing():
        await asyncio.sleep(1)

    await voice_client.disconnect()

@bot.command()
async def stop(ctx):
    # Check if bot is connected to a voice channel
    if ctx.voice_client is None:
        await ctx.send("I'm not connected to a voice channel.")
        return

    # Stop audio if playing
    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()

    # Disconnect
    await ctx.voice_client.disconnect()
    await ctx.send("Stopped playing and disconnected.")

bot.run(DISCORD_TOKEN)