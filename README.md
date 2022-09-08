# InstagramDiscordBot
  Discord Bot for posting feed of multiple Instagram accounts in a server channel
  
## Getting started

### Step 1:
Install dependencies with pip:
```sh
pip install discord requests parse
```

### Step 2:
Open a Web Browser like Mozilla Firefox. Log in to your instagram account (mandatory).
Open the url https://www.instagram.com/instagram/?__a=1&__d=dis in the same Web Browser, then open developer tools with F12.
Go to the network section, and do a refresh with F5. Locate the GET request to https://www.instagram.com/instagram/?__a=1&__d=dis 
and see the request's header. Fill in the parameter values of HEADER in main.py as there are displayed in the request header on your Browser, especially the Cookie.

### Step 3:
Go to the discord developer portal (https://discord.com/developers/applications),
create the application of the bot and copy the token to TOKEN in main.py.
Add the bot's application to your discord server with proper permissions.
Copy the id of the channel the bot will write in to CHANNEL_ID in main.py

### Step 4:
Add the desired instagram accounts to the list INSTAGRAM_ACCOUNTS in main.py
Start the bot
