import sys, os
import json, random, re, typing, asyncio, logging, aiohttp
from datetime import datetime, timedelta
from calendar import monthrange

import discord
from discord.ext import commands

import apiai



__name__ = "SDC.Autobump"
__version__ = "0.3.0"


# ТОКЕН ВАШЕГО СЕЛФ-БОТА
TOKEN = ""
# ТОКЕН ВАШЕГО ОБЫЧНОГО БОТА С ПОДКЛЮЧЕННЫМИ ИНТЕНТАМИ НА СООБЩЕНИЯ
BOT_TOKEN = ""
# СПИСОК ID ЧАТОВ, В КОТОРЫХ НУЖНО БАМПАТЬ (на один сервер лучше 1 канал)
BUMPING_CHANNELS_IDS = []


DISCORD_ROUTE = "https://discord.com/api/v9"

random.seed()


logger = logging.getLogger('bump')
logger.setLevel(logging.DEBUG)
now = datetime.now()
logname = 'bump.log'
try:
    f = open(logname, 'r')
except:
    f = open(logname, 'w')
    f.close()
finally:
    handler = logging.FileHandler(
        filename=logname,
        encoding='utf-8',
        mode='a')
handler.setFormatter(logging.Formatter(
    '%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)



client = commands.Bot(
                        cache_auth=False,
                        command_prefix="...",
                        help_command=None
                    )
inori_client = commands.Bot(
                        intents = discord.Intents.all(),
                        fetch_offline_members = True,
                        max_messages = 2500,
                        command_prefix = ".",
                        help_command = None
                    )

client.async_tasks = []

client.bumping_sup = None
client.bumping_like = None
client.bumping_dbump = None

SECONDS_STOP_UPDATING_BUMP_INFO = 60


@client.event
async def on_command_error(ctx, error):
    pass



async def suping():
    await client.wait_until_ready()

    while True:
        try:
        	for channel_id in BUMPING_CHANNELS_IDS:
	            channel = client.get_channel(channel_id)

	            await make_bump_requests(channel.id, "s.up", 0, cd = 0, attempts = 1)

            await asyncio.sleep(23*60 + random.uniform(7*60, 19*60))
        except Exception as e:
            logger.info(e)
            await asyncio.sleep(60)


async def start_async_tasks():
        await client.wait_until_ready()

        for task in client.async_tasks:
            try:
                task.cancel()
            except Exception as e:
                logger.info(e)

        client.async_tasks = []

        client.async_tasks.append(
            client.loop.create_task(suping())
        )

@client.event
async def on_ready():
    await inori_client.login(BOT_TOKEN, bot=True)
    print('We have logged in as BOT: {0.user}'.format(inori_client))

    print('We have logged in as {0.user}'.format(client))

    await start_async_tasks()

    await asyncio.sleep(30)
    try:
    	for channel_id in BUMPING_CHANNELS_IDS:
	        channel = client.get_channel(channel_id)
	        await make_bump_requests(channel.id, "s.up", 0, cd=0, attempts=0)
    except Exception as e:
        print(e)



what_list = [
    "Че?",
    "??",
    "не понял",
    "ахаха",
    "Ну блин",
    "Нее",
    "Ну неет",
    "Чего?",
    "че",
    "не понял",
    "О чем ты",
    "чего блин?",
    "ты нормальный?",
    "...",
    ":eyes:"
]

is_replying = False

@client.event
async def on_message(message):
    author = message.author
    channel = message.channel
    is_dm = isinstance(channel, discord.DMChannel)
    guild = None if is_dm else channel.guild
    content = message.content

    global is_replying

    if author.id == client.user.id:
        return


    if channel.id in BUMPING_CHANNELS_IDS:
        # Автобампер
        await handle_bump_info(message)


    if is_dm or client.user.mention in message.content or message.content.lower().startswith(client.user.name.lower()):
        if is_replying:
            return

        if author.bot:
            return

        await asyncio.sleep(random.randint(5, 20))

        is_replying = True

        async with channel.typing():
            await asyncio.sleep(random.randint(3, 10))

            content = message.content

            response = None
            try:
                dialogflow = apiai.ApiAI('0dc8f22d98024cbfb58ccd89a6fdbb41').text_request()
                dialogflow.lang = 'ru'
                dialogflow.session_id = 'BatlabAIBot'
                dialogflow.query = content # Посылаем запрос к ИИ с сообщением от юзера
                responseJson = json.loads(dialogflow.getresponse().read().decode('utf-8'))
                response = responseJson['result']['fulfillment']['speech'] # Разбираем JSON и вытаскиваем ответ
                # Если есть ответ от бота - присылаем юзеру, если нет - бот его не понял
            except Exception as e:
                logger.info(e)

            if not response:
                response = random.choice(what_list)

            if len(response) > 10:
                await asyncio.sleep(random.randint(2, 7))

            await channel.send(content=response)

            is_replying = False



def calculate_sdc_ups_reset_delay():
    MOSCOW_UTC_DIFF = 3*60*60
    SDC_MOSCOW_TIME_RESET_AT = 12*60*60
    CD_DAY = 24*60*60

    # Прибавить часовой пояс Москвы UTC+3 (3 часа)
    t_now = datetime.utcnow() + timedelta(seconds = MOSCOW_UTC_DIFF)
    month_day = monthrange(t_now.year, t_now.month)[1]
    milliseconds = t_now.strftime('%Y-%m-%d %H:%M:%S.%f').split('.')[1]
    milliseconds = int(milliseconds) / 1000000
    t_reset_likes = t_now - timedelta(seconds = t_now.hour*3600 + t_now.minute*60 + t_now.second + milliseconds)
    if (t_now.day == 1) and t_now.hour < int(SDC_MOSCOW_TIME_RESET_AT/60/60):
        t_reset_likes = t_reset_likes + timedelta(seconds = SDC_MOSCOW_TIME_RESET_AT)
    elif t_now.day < 15 or ((t_now.day == 15) and t_now.hour < int(SDC_MOSCOW_TIME_RESET_AT/60/60)):
        t_reset_likes = t_reset_likes + timedelta(seconds = (15 - t_now.day) * CD_DAY + SDC_MOSCOW_TIME_RESET_AT)
    else:
        t_reset_likes = t_reset_likes + timedelta(seconds = (month_day - t_now.day + 1) * CD_DAY + SDC_MOSCOW_TIME_RESET_AT)
    ts_reset_likes = t_reset_likes.timestamp() - t_now.timestamp()
    return ts_reset_likes


async def make_bump_requests(channel_id, content, delay, cd=0.9, attempts: int=5):
    if content.lower() == "s.up":
        sdc_ups_reset_delay = calculate_sdc_ups_reset_delay()
        if sdc_ups_reset_delay <= delay:
            delay = sdc_ups_reset_delay + cd
            attempts = 3

    await asyncio.sleep(delay - int(attempts / 2) * cd)

    channel = client.get_channel(channel_id)

    # Для СДК отдельный хандлер прямо тут
    # -------------------------------------------------
    if content.lower() == "s.up":
        async with aiohttp.ClientSession() as session:
            headers = {'authorization': TOKEN, 'Content-Type': 'application/json'}
            payload = {
                "type": 2,
                "application_id": "464272403766444044",
                "guild_id": str(channel.guild.id),
                "channel_id": str(channel.id),
                "data": {
                    "version": "891377101494681661",
                    "id": "891377101494681660",
                    "name": "up",
                    "type": 1
                }
            }
            for i in range(attempts):
                try:
                    await session.post(f"{DISCORD_ROUTE}/interactions", json=payload, headers=headers)

                    await asyncio.sleep(cd)
                except Exception as e:
                    logger.info(e)
        return
    # -------------------------------------------------

    for i in range(attempts):
        try:
            await channel.send(content=content)

            await asyncio.sleep(cd)
        except Exception as e:
            logger.info(e)


async def handle_bump_info(message):
    t_now = datetime.utcnow()
    t_now_ts = int(t_now.timestamp())

    author = message.author
    channel = message.channel
    guild = channel.guild
    content = message.content
    embeds = message.embeds
    embed = embeds[0] if len(embeds) > 0 else None


    # Server-Discord.com
    if author.id == 464272403766444044:
        try:
            bump_ch = await inori_client.fetch_channel(channel.id)
            message = await bump_ch.fetch_message(message.id)

            content = message.content
            embeds = message.embeds
            embed = embeds[0] if len(embeds) > 0 else None
        except Exception as e:
            print(e)

        if not embed:
            return

        em = embed.to_dict()
        description = em.get("description", "")
        re_sup_on_cd = re.match(r'^Up <t:[\d]+:[tTdDfFR]>: <t:([\d]+):[tTdDfFR]>$', description)
        re_sup_upped = re.match(r'^\*\*Успешный Up!\*\*[.\n\\n]{1,2}Время фиксации апа: <t:([\d]+):[tTdDfFR]>$', description)

        # Если САП в кулдауне
        if re_sup_on_cd:
            temp = str(re_sup_on_cd.group(1))
            ts = int(temp)
            count = ts - t_now.timestamp()
        # Если пришло сообщение об успешном САПе
        elif re_sup_upped:
            temp = str(re_sup_upped.group(1))
            ts = int(temp)
            # Прибавить 4 часа кулдаун САПа
            count = ts + 4*60*60 - t_now.timestamp()
        else:
            # Не смог распознать
            return

        if count < SECONDS_STOP_UPDATING_BUMP_INFO and client.bumping_sup:
            return

        if client.bumping_sup:
            try:
                client.bumping_sup.cancel()
            except Exception as e:
                logger.info(e)

        client.bumping_sup = client.loop.create_task(make_bump_requests(channel.id, "s.up", count, cd=1, attempts=3))

        logger.info(f"({guild.name} | {guild.id}) [{channel.name} | {channel.id}] s.up sleep {count}")


    # DiscordServer.info
    if message.webhook_id or (message.author and message.author.id == 575776004233232386):
        return

        try:
            bump_ch = await inori_client.fetch_channel(channel.id)
            message = await bump_ch.fetch_message(message.id)

            content = message.content
            embeds = message.embeds
            embed = embeds[0] if len(embeds) > 0 else None
        except Exception as e:
            print(e)

        if not embed:
            return

        em = embed.to_dict()

        if isinstance(embed.description, str) and "До следующего лайка".lower() in embed.description.lower():
            next_like = embed.timestamp
            t_next_ts = next_like.timestamp() - t_now_ts

            if int(t_next_ts) < SECONDS_STOP_UPDATING_BUMP_INFO and client.bumping_like:
                return


            if client.bumping_like:
                try:
                    client.bumping_like.cancel()
                except Exception as e:
                    logger.info(e)

            client.bumping_like = client.loop.create_task(make_bump_requests(channel.id, "!like", t_next_ts, cd=1, attempts=7))

            logger.info(f"({guild.name} | {guild.id}) [{channel.name} | {channel.id}] !like sleep {t_next_ts}")


    # DISBOARD
    if author.id == 302050872383242240:
        try:
            bump_ch = await inori_client.fetch_channel(channel.id)
            message = await bump_ch.fetch_message(message.id)

            content = message.content
            embeds = message.embeds
            embed = embeds[0] if len(embeds) > 0 else None
        except Exception as e:
            print(e)

        if not content:
            return

        if "поднять" in content.lower():
            t_next_ts = 2 * 60 * 60


            if client.bumping_dbump:
                try:
                    client.bumping_dbump.cancel()
                except Exception as e:
                    logger.info(e)

            client.bumping_dbump = client.loop.create_task(make_bump_requests(channel.id, "!d bump", t_next_ts, cd=1))

            logger.info(f"({guild.name} | {guild.id}) [{channel.name} | {channel.id}] !d bump sleep {t_next_ts}")



client.run(TOKEN, bot=False)
