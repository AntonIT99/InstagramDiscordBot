import traceback
from typing import Optional

import discord
import requests
from discord.ext import commands, tasks
from parse import parse

# Should the bot update existing posts to get the latest number of likes and comments
UPDATE_POSTS = True
# Display debug log when updating a post to track differences
UPDATE_DEBUG_LOG = True
# Token of the bot
TOKEN = 'enter your bot token here' # enter your bot token here
# instagram account names
INSTAGRAM_ACCOUNTS = ['instagram', 'instagramforbusiness', 'meta']
# channel id where the images are posted
CHANNEL_ID = 1234567890 # replace by your channel id
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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:108.0) Gecko/20100101 Firefox/108.0"
}

bot = commands.Bot(command_prefix="$", intents=discord.Intents.all())


class Author:

    def __init__(self, username: str, full_name: str, profile_pic_url: str):
        self.username = str(username)
        self.full_name = str(full_name)
        self.profile_pic_url = str(profile_pic_url)

    def __eq__(self, other):
        return (isinstance(other, Author) and
                self.username == other.username and
                self.full_name == other.full_name and
                self.profile_pic_url == other.profile_pic_url)


class InstagramPost:

    def __init__(self, author: Author, image_code: str, image_url: str, description: str, likes: int, comments: int):
        self.author = author
        self.image_code = str(image_code)
        self.image_url = str(image_url)
        self.description = str(description)
        self.likes = int(likes)
        self.comments = int(comments)

    def __eq__(self, other):
        return (isinstance(other, InstagramPost) and
                self.author == other.author and
                self.image_code == other.image_code and
                self.image_url == other.image_url and
                self.description == other.description and
                self.likes == other.likes and
                self.comments == other.comments)


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


async def update_from_instagram(channel: discord.channel):
    last_published_posts = await read_published_messages(channel)
    posts_from_all_authors = {}
    for username in INSTAGRAM_ACCOUNTS:
        author = get_user_data(username)
        if author is not None:
            posts_from_all_authors[username] = get_last_posts_from_instagram(author)
        else:
            print(username + ": Failed to update")

    for username in posts_from_all_authors:
        new_images = 0
        updated_images = 0
        for code in posts_from_all_authors[username]:
            if code not in [post.image_code for post in last_published_posts]:
                new_images = await post_image(channel, posts_from_all_authors[username][code], new_images)
            elif UPDATE_POSTS:
                message = await get_published_message_from_image_code(channel, code)
                if message is not None:
                    updated_images = await update_image(message, posts_from_all_authors[username][code], updated_images)
        if new_images > 0:
            print("[{}]: {} new image{} to post in discord".format(username, new_images, "s" if new_images > 1 else ""))
        else:
            print("[{}]: No new image to post in discord".format(username))
        if updated_images > 0:
            print("[{}]: {} image{} updated in discord".format(username, updated_images, "s" if updated_images > 1 else ""))


SHORTCODE_URL = "https://www.instagram.com/p/{}/"
AUTHOR_URL = "https://www.instagram.com/{}/"
TITLE_STR = "Neuer Beitrag von @{}"
FOOTER_STR = "Gefällt {} Mal\n{} Kommentare"


# generate an embed from an InstagramPost
def create_embed(post: InstagramPost) -> discord.Embed:
    embed = discord.Embed(title=TITLE_STR.format(post.author.username),
                          url=SHORTCODE_URL.format(post.image_code),
                          description=post.description,
                          color=COLOR)
    embed.set_author(name=post.author.full_name,
                     url=AUTHOR_URL.format(post.author.username),
                     icon_url=post.author.profile_pic_url)
    embed.set_image(url=post.image_url)
    embed.set_footer(text=FOOTER_STR.format(post.likes, post.comments))
    return embed


# read all published messages in the channel and return the corresponding list of InstagramPost
async def read_published_messages(channel: discord.channel) -> list:
    last_published_posts = []
    async for message in channel.history(limit=MESSAGE_HISTORY_LIMIT):
        post = get_post_from_discord_message(message)
        if post is not None:
            last_published_posts.append(post)
    return last_published_posts


# return an InstagramPost from a discord message
def get_post_from_discord_message(message: discord.message) -> Optional[InstagramPost]:
    if len(message.embeds) > 0:
        embed = message.embeds[0]
        username = parse(AUTHOR_URL, str(embed.author.url))
        shortcode = parse(SHORTCODE_URL, str(embed.url))
        if username is not None and shortcode is not None:
            username = username[0]
            shortcode = shortcode[0]
            description = str(embed.description or '')
            image_url = str(embed.image.url or '')
            author_name = str(embed.author.name or '')
            author_icon_url = str(embed.author.icon_url or '')
            likes = 0
            comments = 0
            footer = parse(FOOTER_STR, str(embed.footer.text))
            if footer is not None:
                likes = int(footer[0])
                comments = int(footer[1])
            author = Author(username, author_name, author_icon_url)
            return InstagramPost(author, shortcode, image_url, description, likes, comments)
    return None


# get discord message with embed image from the image code
async def get_published_message_from_image_code(channel: discord.channel, code: str) -> discord.message:
    async for message in channel.history(limit=MESSAGE_HISTORY_LIMIT):
        if len(message.embeds) > 0:
            embed = message.embeds[0]
            shortcode = parse(SHORTCODE_URL, str(embed.url))
            if shortcode is not None:
                if code == shortcode[0]:
                    return message
    return None


# post embedded image to discord channel
async def post_image(channel: discord.channel, post: InstagramPost, counter: int):
    await channel.send(embed=create_embed(post))
    return counter + 1


# update existing embedded image
async def update_image(message: discord.message, new_post: InstagramPost, counter: int):
    existing_post = get_post_from_discord_message(message)
    if new_post != existing_post:
        new_embed = create_embed(new_post)
        if UPDATE_DEBUG_LOG:
            print_update_log(new_post, existing_post)
        await message.edit(embed=new_embed)
        counter += 1
    return counter


# return an Author from the user data of the specified account
def get_user_data(username: str) -> Optional[Author]:
    response = requests.get("https://www.instagram.com/{}/?__a=1&__d=dis".format(username), headers=HEADER, timeout=TIMEOUT)
    try:
        user_data = response.json()["graphql"]["user"]
        return Author(username, user_data["full_name"], user_data["profile_pic_url"])
    except Exception:
        traceback.print_exc()
        return None


# return a dict of InstagramPost from the data of the latest images available from the specified Author
def get_last_posts_from_instagram(author: Author) -> Optional[dict]:
    response = requests.get("https://www.instagram.com/{}/?__a=1&__d=dis".format(author.username), headers=HEADER, timeout=TIMEOUT)
    try:
        images = {}
        images_list = response.json()["graphql"]["user"]["edge_owner_to_timeline_media"]["edges"]
        for image_data in images_list:
            image_code = str(image_data["node"]["shortcode"])
            image_url = str(image_data["node"]["display_url"])
            description = ""
            desc_txt = image_data["node"]["edge_media_to_caption"]["edges"]
            if len(desc_txt) > 0:
                if "node" in desc_txt[0].keys():
                    if "text" in desc_txt[0]["node"].keys():
                        description = str(desc_txt[0]["node"]["text"])
            likes = int(image_data["node"]["edge_liked_by"]["count"])
            comments = int(image_data["node"]["edge_media_to_comment"]["count"])
            images[image_code] = InstagramPost(author, image_code, image_url, description, likes, comments)
        return images
    except Exception:
        traceback.print_exc()
        return None


def print_update_log(new: InstagramPost, old: InstagramPost):
    if new.author.username != old.author.username:
        print("[{}] {}: author.username {} changed to {}".format(new.author.username, new.image_code, old.author.username, new.author.username))
    if new.author.full_name != old.author.full_name:
        print("[{}] {}: author.full_name {} changed to {}".format(new.author.username, new.image_code, old.author.full_name, new.author.full_name))
    if new.author.profile_pic_url != old.author.profile_pic_url:
        print("[{}] {}: author.profile_pic_url {} changed to {}".format(new.author.username, new.image_code, old.author.profile_pic_url, new.author.profile_pic_url))
    if new.image_code != old.image_code:
        print("[{}] {}: image_url {} changed to {}".format(new.author.username, new.image_code, old.image_code, new.image_code))
    if new.image_url != old.image_url:
        print("[{}] {}: image_url {} changed to {}".format(new.author.username, new.image_code, old.image_url, new.image_url))
    if new.description != old.description:
        print("[{}] {}: description {} changed to {}".format(new.author.username, new.image_code, old.description, new.description))
    if new.likes != old.likes:
        print("[{}] {}: {} likes changed to {} likes".format(new.author.username, new.image_code, old.likes, new.likes))
    if new.comments != old.comments:
        print("[{}] {}: {} comments changed to {} comments".format(new.author.username, new.image_code, old.comments, new.comments))


if __name__ == "__main__":
    bot.run(TOKEN)
