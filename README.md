# Simple Discord YouTube Player
This is a very simple and lightweight Discord bot that plays audio of youtube videos in Discord calls. It uses Discord.py to interface with Discord and yt-dlp to handle youtube downloading.

This bot works by taking a youtube link, downloading the video's audio as mp3, and then plays that mp3 file over discord. This is to make it as simple as possible and not deal with streaming the audio. The downside is that it takes some time to play the audio after you send the link, but works fine. It deletes the audio once it's done.

# How to Use
Once the bot is installed and running (see below), it has two commands
- !play <youtube url>  -- Bot will join the voice channel you are currently in and start to play the audio. It announces it's downloading the audio so you know to wait a few seconds for it to download
- !stop -- stops the bot if it's currently playing

# Limitations
This bot is very basic so it has some limitations
- No queue function. You have to !stop or wait for the bot to finish to play different audio
- Does **NOT** work on multiple servers. If this bot is playing audio on two different Discord server they will overwrite each other
- Hard coded with a 600 second video limit, this can be edited in the code
- No volume control, each person needs to turn the bots volume down on their own in Discord



# todo
- [ ] Add queue functionality
- [ ] Support more than one server

# Installation
To run the bot yourself you can follow these basic steps. This assumes you know how to setup and use a basic Python environment. Installation assumes Ubuntu Linux.

- Clone repo and create .env file to hold our secrets:
```
git clone https://github.com/tylerwight/simple-discord-yt-player
cd simple-discord-yt-player
touch .env
```

- Create a new bot/app in the Discord Developer Portal
- Generate an OAuth2 link for the bot to join with voice permissions and join the bot to your Discord server
- Get your bot's API token and put it in the .env file like this:
.env:
```
DISCORD_TOKEN = "<your token here>"
```

- Install Python libraries and ffmpeg
```
sudo apt install ffmpeg
pip install -r requirements.txt
```
- Run bot
```
python3 main.py
```