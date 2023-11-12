import asyncio
import logging
import os
from logging.handlers import RotatingFileHandler

import discord
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

TEST_GUILD = discord.Object(os.getenv('TEST_GUILD'))


def init_logger(_logger: logging.Logger) -> None:
    _logger.setLevel(logging.DEBUG)

    f_file = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', style="{")
    f_console = logging.Formatter('[{levelname:<8}] {name}: {message}', style="{")

    fh_debug = RotatingFileHandler(
        filename='debug.log',
        encoding='utf-8',
        maxBytes=32 * 1024 * 1024,  # 32 MiB
        backupCount=2,  # Rotate through 2 files
    )
    fh_debug.setLevel(logging.DEBUG)
    fh_debug.setFormatter(f_file)

    fh_error = RotatingFileHandler(
        filename='error.log',
        encoding='utf-8',
        maxBytes=32 * 1024 * 1024,  # 32 MiB
        backupCount=2,  # Rotate through 2 files
    )
    fh_error.setLevel(logging.ERROR)
    fh_error.setFormatter(f_file)

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(f_console)

    _logger.addHandler(fh_debug)
    _logger.addHandler(fh_error)
    _logger.addHandler(console)


logger = logging.getLogger(__name__)
init_logger(logger)


class MyClient(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)

    async def on_ready(self) -> None:
        logger.info(f'{self.user}({self.user.id}) CONNECTED!')

    async def setup_hook(self) -> None:
        await self.tree.sync(guild=None)  # TEST_GUILD)


client = MyClient()


@client.tree.command(name='ping', description='get latency')  # , guild=TEST_GUILD)
async def ping(interaction: discord.Interaction):
    """Sends latency in ms."""
    await interaction.response.send_message(f'Pong, {round(client.latency * 1000)}ms')


@client.event
async def on_voice_state_update(_member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    if _member == client.user:
        return

    if after.channel is None:
        return

    if 'general' not in after.channel.name.lower():
        return

    if before.channel is not None and 'general' in before.channel.name.lower():
        return

    # noinspection PyTypeChecker
    voice_client: discord.VoiceClient = discord.utils.get(client.voice_clients, guild=after.channel.guild)
    if voice_client is not None and voice_client.is_connected():
        logger.debug(f'already connected to a voice channel')
        return

    event = asyncio.Event()

    def after_f(_error):
        logger.debug(f'playing finished')
        event.set()

    voice_client: discord.VoiceClient = await after.channel.connect()
    voice_client.play(discord.FFmpegOpusAudio('Hello_there.mp3'), after=after_f)

    await event.wait()
    await voice_client.disconnect()


client.run(os.getenv('TOKEN'))  # , log_level=logging.DEBUG)
