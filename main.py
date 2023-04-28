import functools
import locale
import traceback
from datetime import date, datetime
from time import sleep
from typing import Optional

import discord
import requests
import typing
from discord.ext import commands, tasks
from parse import parse

import config

bot = commands.Bot(command_prefix=config.COMMAND_PREFIX, intents=discord.Intents.all())


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

    def __init__(self, author: Author, image_code: str, image_url: str, description: str, likes: int, comments: int, post_date: date):
        self.author = author
        self.image_code = str(image_code)
        self.image_url = str(image_url)
        self.description = str(description)
        self.likes = int(likes)
        self.comments = int(comments)
        self.post_date = post_date

    def __eq__(self, other):
        return (isinstance(other, InstagramPost) and
                self.author == other.author and
                self.image_code == other.image_code and
                self.image_url == other.image_url and
                self.description == other.description and
                self.likes == other.likes and
                self.comments == other.comments and
                self.post_date == other.post_date)


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
    await update_from_instagram()


@tasks.loop(seconds=config.UPDATE_INTERVAL)
async def updater():
    await update_from_instagram()
    if config.AUTO_EXIT:
        await bot.close()


async def update_from_instagram():
    messages_of_instagram_posts = await read_published_messages()
    posts_from_all_authors = {}
    await run_blocking(fetch_posts_from_instagram, posts_from_all_authors)

    for username in posts_from_all_authors:
        new_images = 0
        updated_images = 0
        for code in posts_from_all_authors[username]:
            if code not in messages_of_instagram_posts.keys():
                new_images = await post_image(posts_from_all_authors[username][code], new_images)
            elif config.UPDATE_POSTS:
                message = messages_of_instagram_posts[code]
                if message is not None:
                    updated_images = await update_image(message, posts_from_all_authors[username][code], updated_images)
        if new_images > 0:
            print("[{}]: {} new image{} to post in discord".format(username, new_images, "s" if new_images > 1 else ""))
        else:
            print("[{}]: No new image to post in discord".format(username))
        if updated_images > 0:
            print("[{}]: {} image{} updated in discord".format(username, updated_images, "s" if updated_images > 1 else ""))


# Runs a blocking function in a non-blocking way
async def run_blocking(blocking_func: typing.Callable, *args, **kwargs) -> typing.Any:
    func = functools.partial(blocking_func, *args, **kwargs)
    return await bot.loop.run_in_executor(None, func)


def fetch_posts_from_instagram(posts_from_all_authors: dict):
    for username in config.INSTAGRAM_ACCOUNTS:
        user_id, author = get_user_data(username)
        if user_id is not None and author is not None:
            posts_from_all_authors[username] = get_posts_from_instagram(user_id, author)
        else:
            print("[{}]: Failed to update: can not retrieve account data".format(username))


SHORTCODE_URL = "https://www.instagram.com/p/{}/"
AUTHOR_URL = "https://www.instagram.com/{}/"
TITLE_STR = "Neuer Beitrag von @{}"
FOOTER_STR = "Gefällt {} Mal\n{} Kommentare\n{}"
DATE_FORMAT = "%B %d, %Y"


# generate an embed from an InstagramPost
def create_embed(post: InstagramPost) -> discord.Embed:
    embed = discord.Embed(title=TITLE_STR.format(post.author.username),
                          url=SHORTCODE_URL.format(post.image_code),
                          description=post.description,
                          color=config.COLOR)
    embed.set_author(name=post.author.full_name,
                     url=AUTHOR_URL.format(post.author.username),
                     icon_url=post.author.profile_pic_url)
    embed.set_image(url=post.image_url)
    embed.set_footer(text=FOOTER_STR.format(post.likes, post.comments, post.post_date.strftime(DATE_FORMAT)))
    return embed


# read all published messages in the channel
async def read_published_messages() -> dict:
    messages = {}
    async for message in bot.get_channel(config.CHANNEL_ID).history(limit=config.MESSAGE_HISTORY_LIMIT):
        if message.author.id == bot.user.id:
            post = get_post_from_discord_message(message)
            if post is not None:
                messages[post.image_code] = message
    return messages


# return an InstagramPost from a discord message
def get_post_from_discord_message(message: discord.Message) -> Optional[InstagramPost]:
    if len(message.embeds) > 0:
        embed = message.embeds[0]
        shortcode = parse(SHORTCODE_URL, str(embed.url))
        if shortcode is not None:
            shortcode = shortcode[0]
            username = parse(AUTHOR_URL, str(embed.author.url))
            if username is not None:
                username = username[0]
            else:
                username = ""
            description = str(embed.description or '')
            image_url = str(embed.image.url or '')
            author_name = str(embed.author.name or '')
            author_icon_url = str(embed.author.icon_url or '')
            likes = 0
            comments = 0
            post_date = date(2000, 1, 1)
            footer = parse(FOOTER_STR, str(embed.footer.text))
            if footer is not None:
                likes = int(footer[0])
                comments = int(footer[1])
                post_date = datetime.strptime(str(footer[2]), DATE_FORMAT).date()
            author = Author(username, author_name, author_icon_url)
            return InstagramPost(author, shortcode, image_url, description, likes, comments, post_date)
        else:
            return None
    return None


# post embedded image to discord channel
async def post_image(post: InstagramPost, counter: int) -> int:
    if post.post_date >= config.POST_DATE_LIMIT:
        await bot.get_channel(config.CHANNEL_ID).send(embed=create_embed(post))
        return counter + 1
    return counter


# update existing embedded image
async def update_image(message: discord.Message, new_post: InstagramPost, counter: int) -> int:
    existing_post = get_post_from_discord_message(message)
    if new_post != existing_post:
        new_embed = create_embed(new_post)
        if config.DEBUG_LOG:
            print_update_log(new_post, existing_post)
        if message.author.id == bot.user.id:
            await message.edit(embed=new_embed)
            counter += 1
    return counter


# return an Author and its user id from the user data of the specified account
def get_user_data(username: str) -> (Optional[str], Optional[Author]):
    response = requests.get("https://www.instagram.com/{}/?__a=1&__d=dis".format(username), headers=config.HEADER, timeout=config.TIMEOUT)
    try:
        user_data = response.json()["graphql"]["user"]
        return user_data["id"], Author(username, user_data["full_name"], user_data["profile_pic_url_hd"])
    except Exception:
        traceback.print_exc()
        return None, None


# return a dict of InstagramPost from the data of the latest images available from the specified Author
def get_posts_from_instagram(user_id: str, author: Author) -> dict:
    images = {}
    json = {}

    try:
        if config.DEBUG_LOG:
            print("[{}]: fetching latest images...".format(author.username))
        json = get_json_from_graphql_query(user_id)
        images_count = int(json["data"]["user"]["edge_owner_to_timeline_media"]["count"])
        if config.FETCHING_LIMIT is not None and images_count > config.FETCHING_LIMIT:
            images_count = config.FETCHING_LIMIT
        step = len(json["data"]["user"]["edge_owner_to_timeline_media"]["edges"])
    except Exception:
        traceback.print_exc()
        if "message" in json:
            print(json["message"])
        return images

    fetched_images = 0

    end_cursor = str(json["data"]["user"]["edge_owner_to_timeline_media"]["page_info"]["end_cursor"])
    images_list = json["data"]["user"]["edge_owner_to_timeline_media"]["edges"]

    for i in range(0, images_count, step):

        for image_data in images_list:
            image_code = str(image_data["node"]["shortcode"])
            image_url = str(image_data["node"]["display_url"])
            description = ""
            caption_data = image_data["node"]["edge_media_to_caption"]["edges"]
            if len(caption_data) > 0:
                if "node" in caption_data[0].keys():
                    if "text" in caption_data[0]["node"].keys():
                        description = str(caption_data[0]["node"]["text"])
            likes = int(image_data["node"]["edge_media_preview_like"]["count"])
            comments = int(image_data["node"]["edge_media_to_comment"]["count"])
            timestamp = int(image_data["node"]["taken_at_timestamp"])
            images[image_code] = InstagramPost(author, image_code, image_url, description, likes, comments, date.fromtimestamp(timestamp))
            fetched_images += 1

        if fetched_images != images_count:
            try:
                if config.DEBUG_LOG:
                    print("[{}]: fetching images {} to {}...".format(author.username, fetched_images,
                                                                     fetched_images + step - 1 if fetched_images + step - 1 < images_count else images_count - 1))
                json = get_json_from_graphql_query(user_id, end_cursor)
                end_cursor = str(json["data"]["user"]["edge_owner_to_timeline_media"]["page_info"]["end_cursor"])
                images_list = json["data"]["user"]["edge_owner_to_timeline_media"]["edges"]
            except Exception:
                traceback.print_exc()
                if "message" in json:
                    print(json["message"])
                print("[{}]: failed to fetching images, retrying in 5s...".format(author.username))
                sleep(5)
                try:
                    print("[{}]: retrying to fetch images {} to {}...".format(author.username,
                                                                              fetched_images, fetched_images + step - 1 if fetched_images + step - 1 < images_count else images_count - 1))
                    json = get_json_from_graphql_query(user_id, end_cursor)
                    end_cursor = str(json["data"]["user"]["edge_owner_to_timeline_media"]["page_info"]["end_cursor"])
                    images_list = json["data"]["user"]["edge_owner_to_timeline_media"]["edges"]
                except Exception:
                    traceback.print_exc()
                    if "message" in json:
                        print(json["message"])
                    if config.DEBUG_LOG:
                        print("[{}]: abort the fetching process".format(author.username))
                    break

    print("[{}]: {} images fetched from instagram".format(author.username, fetched_images))
    return images


def get_json_from_graphql_query(user_id: str, end_cursor=""):
    if end_cursor:
        response = requests.get("https://www.instagram.com/graphql/query/?query_id=17888483320059182&id={}&first=12&after={}".format(user_id, end_cursor),
                                headers=config.HEADER, timeout=config.TIMEOUT)
    else:
        response = requests.get("https://www.instagram.com/graphql/query/?query_id=17888483320059182&id={}&first=12".format(user_id),
                                headers=config.HEADER, timeout=config.TIMEOUT)
    return response.json()


def print_update_log(new: InstagramPost, old: InstagramPost):
    if new.author.username != old.author.username:
        print("[{}] {}: author.username {} changed to {}".format(new.author.username, new.image_code, old.author.username, new.author.username))
    if new.author.full_name != old.author.full_name:
        print("[{}] {}: author.full_name {} changed to {}".format(new.author.username, new.image_code, old.author.full_name, new.author.full_name))
    if new.author.profile_pic_url != old.author.profile_pic_url:
        print("[{}] {}: author.profile_pic_url changed".format(new.author.username, new.image_code))
    if new.image_code != old.image_code:
        print("[{}] {}: image_code {} changed to {}".format(new.author.username, new.image_code, old.image_code, new.image_code))
    if new.image_url != old.image_url:
        print("[{}] {}: image_url changed".format(new.author.username, new.image_code))
    if new.description != old.description:
        print("[{}] {}: description {} changed to {}".format(new.author.username, new.image_code, old.description, new.description))
    if new.likes != old.likes:
        print("[{}] {}: {} likes changed to {} likes".format(new.author.username, new.image_code, old.likes, new.likes))
    if new.comments != old.comments:
        print("[{}] {}: {} comments changed to {} comments".format(new.author.username, new.image_code, old.comments, new.comments))
    if new.post_date != old.post_date:
        print("[{}] {}: post_date {} changed to {}".format(new.author.username, new.image_code, old.post_date, new.post_date))


if __name__ == "__main__":
    locale.setlocale(locale.LC_TIME, "de_DE")  # German locale
    bot.run(config.TOKEN)
