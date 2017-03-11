# RockeMap-BasicBot
This is a simple webhook modification, along with a simple-n-single file bot, and 
also using 2 external files for Pokemon Name, and Pokemon Movesets

You can modify your RocketMap (pogom/webhook.py) and add the blocks of scripts I used (starting with a wide/loud comment), 
or (RAW) copy this file and paste it into your webhook.py file.

-I am not a python expert so I bet there are people out there that can make something better.

# How it works?
First, create a channel for all the information pushed by webhook. Only allowing you and your bot access to it.

Second, Create any necessary channels, and webhooks for each channel.

Third, Modify the bot files and input the right information - ie: bot token, channel names, colors, etc.

# REQUIRED:
1) Node.js https://nodejs.org/en/download/  

2) Discord.js (npm install discord.js) 

3) Bot Token: https://discordapp.com/developers/applications/me  

4) And assign bot access to your server: https://finitereality.github.io/permissions/?v=0

# LAUNCHING IT:
Using command promp or bash: node SimpleBot.js
-You close that window, the bot connection is terminated
Optional: you can install pm2 to have it run in the background

# PM2:
PM2 allowes you to run processes in the background, you can access PM2 from anywhere, but for a process to start it needs to come from the folder where the file is.
npm install pm2 -g
pm2 start SimpleBot.js

To modify the file and keep bot up-to-date (auto reloading):
pm2 start SimpleBot.js --watch

Other Commands:
pm2 log (display log)
pm2 list (display a list of running processes)
pm2 stop NAME/ID
