from datetime import date, timedelta

# Post date limit, prevent the bot to post too old images from instagram, will not affect updating of already posted images
POST_DATE_LIMIT = date.today() - timedelta(days=60)
# Should the bot update existing posts to get the latest number of likes and comments
UPDATE_POSTS = True
# Display additional logs
DEBUG_LOG = True
# Token of the bot
TOKEN = 'enter your bot token here' # enter your bot token here
# instagram account names
INSTAGRAM_ACCOUNTS = ['instagram', 'instagramforbusiness', 'meta']
# channel id where the images are posted
CHANNEL_ID = 1234567890
# command prefix for "update" and "ping" bot commands
COMMAND_PREFIX = "$"
# maximal number of images that should be fetched from each instagram account, set to None for no limit
FETCHING_LIMIT = None
# limit of the message history read when checking if latest instagram publications have already been posted in the channel, set to None for no limit
MESSAGE_HISTORY_LIMIT = None
# color of the messages
COLOR = 0x05c0ec
# close the bot after one update instead of updating periodically with a specified time interval
AUTO_EXIT = False
# time in seconds after which an update is performed
UPDATE_INTERVAL = 3600
# requests timeout
TIMEOUT = 5
# header for sending requests to Instagram
HEADER = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Encoding": "de,en-US;q=0.7,en;q=0.3",
    "Connection": "keep-alive",
    "Cookie": "csrftoken=enter your cookie here", # enter your cookie from your web browser here
    "Host": "www.instagram.com",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "cross-site",
    "TE": "trailers",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:108.0) Gecko/20100101 Firefox/108.0"
}
