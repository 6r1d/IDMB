"""
Hyperledger Iroha Discord moderation bot.
"""

from os import getenv
from os.path import isdir, isfile
from logging import basicConfig, INFO, info
from signal import signal, SIGINT, default_int_handler
from json import load
from pathlib import Path
from argparse import ArgumentParser
from discord.ext import commands
from discord import Message, Intents
from nltk import download as nltk_download
from nltk.tokenize import word_tokenize

ROOT_DIR = current_file_path = Path(__file__).parent

def file_path(fpath: str) -> Path:
    """
    Ensure that the supplied input is a valid file.

    Compared to Argparse's FileType(), this function
    does not require the user to set a way of interaction with a file.

    Args:
        fpath (str): file location

    Returns:
        Path: A Path object representing the validated file path.

    Raises:
        FileNotFoundError: If the fpath does not exist or is not a file.
    """
    if not isfile(fpath):
        raise FileNotFoundError(f'The file "{fpath}" does not exist.')
    if isdir(fpath):
        raise IsADirectoryError(f"'{fpath}' is a directory, not a file.")
    return Path(fpath)

def get_arguments():
    """
    Returns:

        (argparse.Namespace): a namespace with a path to the config file.
    """
    parser = ArgumentParser(description="Iroha Discord Moderation Bot")
    parser.add_argument(
        '-c',
        '--config_path',
        help='Path to the configuration file',
        required=True,
        type=file_path
    )
    return parser.parse_args()

def detect_word_threshold(text, word_pairs, threshold):
    """
    Detects if the occurrence of specified words and their pairs in a given text 
    meets or exceeds a specified threshold.

    Args:
        text (str): The text to be analyzed.
        word_pairs (dict): A dictionary where each key is a word and its value
                           is a list of associated words (pairs).
        threshold (int): The minimum count of occurrences required
                         to trigger a return.

    Returns:
        list or None: A list containing a word from the word_pairs
                      and its count if the threshold is met or exceeded; 
                      otherwise, None.
    """
    # Convert the text to lowercase and split into words for easier comparison
    words_in_text = [word.lower() for word in word_tokenize(text)]
    # Iterate over each word and its pairs
    for word, pairs in word_pairs.items():
        count = 0
        # Count occurrences of the word and its pairs in the text
        if word in words_in_text:
            count += words_in_text.count(word)
            for pair in pairs:
                count += words_in_text.count(pair)
        # Check if the count meets or exceeds the threshold
        if count >= threshold:
            return [word, count]
    # If no word meets the threshold
    return None

# pylint: disable=R0901
class ModerationBot(commands.Bot):
    """
    A Discord bot that looks for word occurences matching
    spam and cleans them up.
    """
    def __init__(self, config_path):
        # Load the config
        with open(config_path, 'r', encoding='utf-8') as config_file:
            self.config = load(config_file)
        # Configure the Discord intents required for the moderation
        intents = Intents(messages=True, message_content=True, guilds=True)
        # Initialize the class with the parent class init method
        super().__init__(
            command_prefix='/',
            intents=intents
        )
        # Load the restricted pairs
        with open(ROOT_DIR / 'restricted_pairs.json', 'r', encoding='utf-8') as rp_file:
            self.restricted_pairs = load(rp_file)
        # Load the unicode translation table
        with open(ROOT_DIR / 'unicode_translation_table.json', 'r', encoding='utf-8') \
            as utt_file:
            self.unicode_translation_table = load(utt_file)

    async def on_message(self, message: Message):
        """
        Handle a message, processing the commands when needed.

        Args:
            message (Message): a message to handle
        """
        # Ignore messages from the bot itself
        if message.author == self.user or \
           message.channel.__class__.__name__ != 'TextChannel':
            return
        # Check the channel name
        if message.channel.name not in self.config.get('allowed_channels', []):
            return
        # Translate the message content to avoid wide latin and other spammer tricks
        content = message.content.translate(self.unicode_translation_table)
        # Delete the message if it contains two or more of the monitored words
        detection = detect_word_threshold(message.content, self.restricted_pairs, 2)
        if detection:
            author = message.author.name
            content = message.content
            await message.delete()
            info(f'Removed a message from "{author}": "{content}" | {detection[1]}')

if __name__ == '__main__':
    # Configure logging
    basicConfig(
        filename='mod_bot.log', filemode='a', level=INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    # Map SIGINT to KeyboardInterrupt
    signal(SIGINT, default_int_handler)
    # Prepare NLTK for the word splitting
    nltk_download('punkt')
    # Retrieve the command-line arguments
    args = get_arguments()
    # Setup the bot instance
    bot_instance = ModerationBot(args.config_path)
    # Get a token
    token = getenv('IROHA_DISCORD_MODBOT_TOKEN')
    # Start a bot, handle keyboard interrupts
    try:
        bot_instance.loop.run_until_complete( bot_instance.start(token) )
    except KeyboardInterrupt:
        bot_instance.loop.run_until_complete( bot_instance.close() )
    finally:
        bot_instance.loop.close()
