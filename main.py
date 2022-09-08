import discord
import requests
from discord.ext import commands, tasks
from parse import parse

# Token of the bot
TOKEN = 'enter your bot token here' # enter your bot token here
# instagram account names
INSTAGRAM_ACCOUNTS = ['instagram', 'instagramforbusiness', 'meta']
# channel id where the images are posted
CHANNEL_ID = 12345678 # enter your channel id here
# limit of the message history read when checking if latest instagram publications have already been posted in the channel
MESSAGE_HISTORY_LIMIT = 100
# color of the messages
COLOR = 0x05c0ec
# time in seconds after which an update check is performed
UPDATE_INTERVAL = 3600
# requests timeout
TIMEOUT = 5
# header for sending requests to Instagram
HEADER = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Encoding": "de,en-US;q=0.7,en;q=0.3",
        "Connection": "keep-alive",
        "Cookie": "enter your cookie here", # enter your cookie here
        "Host": "www.instagram.com",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "TE": "trailers",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0"
}

bot = commands.Bot(command_prefix="$", intents=discord.Intents.all())


@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    updater.start()


@bot.event
async def on_message(message):
    await bot.process_commands(message)


@bot.command()
async def ping(ctx):
    print("Ping received")
    await ctx.channel.send('pong')


@bot.command()
async def update(ctx):
    print("Force updating")
    await update_from_instagram(bot.get_channel(CHANNEL_ID))


@tasks.loop(seconds=UPDATE_INTERVAL)
async def updater():
    await update_from_instagram(bot.get_channel(CHANNEL_ID))


async def update_from_instagram(channel):
    last_published_images_codes = []
    async for message in channel.history(limit=MESSAGE_HISTORY_LIMIT):
        for embed in message.embeds:
            code = parse('https://www.instagram.com/p/{}/', embed.url)
            if code is not None:
                last_published_images_codes.append(str(code[0]))
    images_data = {}
    users_data = {}
    for username in INSTAGRAM_ACCOUNTS:
        user_data = get_user_data(username)
        if user_data is not None:
            users_data[username] = user_data
            images_data[username] = get_last_image_data(user_data)
        else:
            print(username + ": Failed to update")

    for username in images_data:
        if images_data[username]["shortcode"] not in last_published_images_codes:
            await post_image(channel, username, users_data[username], images_data[username])
            print(username + ": New image to post in discord")
        else:
            print(username + ": No new image to post in discord")


# post embedded image to discord channel
async def post_image(channel, username, user_data, image_data):
    embed = discord.Embed(title="Neuer Beitrag von @" + str(username),
                          url="https://www.instagram.com/p/{}/".format(image_data["shortcode"]),
                          description=image_data["edge_media_to_caption"]["edges"][0]["node"]["text"],
                          color=COLOR)
    embed.set_author(name=user_data["full_name"],
                     url="https://www.instagram.com/{}/".format(username),
                     icon_url=user_data["profile_pic_url"])
    embed.set_image(url=image_data["display_url"])
    embed.set_footer(text="Gefällt {} Mal\n{} Kommentare".format(image_data["edge_liked_by"]["count"], image_data["edge_media_to_comment"]["count"]))
    await channel.send(embed=embed)


# returns json data of the specified account
def get_user_data(username):
    response = requests.get("https://www.instagram.com/" + str(username) + "/?__a=1&__d=dis", headers=HEADER, timeout=TIMEOUT)
    try:
        return response.json()["graphql"]["user"]
    except:
        return None


# returns json data of the latest image available on the specified instagram account
def get_last_image_data(user_data):
    return user_data["edge_owner_to_timeline_media"]["edges"][0]["node"]


if __name__ == "__main__":
    bot.run(TOKEN)
