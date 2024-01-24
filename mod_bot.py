"""
Hyperledger Iroha Discord moderation bot.
"""

from os import getenv
from json import load
from signal import signal, SIGINT, default_int_handler
from logging import basicConfig, INFO, info
from discord.ext import commands
from discord import Message, Intents

def detect_world_threshold(text, word_pairs, threshold):
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
    words_in_text = text.lower().split()
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

class ModerationBot(commands.Bot):
    """
    A Discord bot that looks for word occurences matching
    spam and cleans them up.
    """

    def __init__(self):
        # Load the options
        with open('./options.json', 'r', encoding='utf-8') as options_file:
            self.options = load(options_file)
        # Configure the Discord intents required for the moderation
        intents = Intents(messages=True, message_content=True, guilds=True)
        # Initialize the class with the parent class init method
        super().__init__(
            command_prefix='/',
            intents=intents
        )
        # Load the restricted pairs
        with open('./restricted_pairs.json', 'r', encoding='utf-8') as rp_file:
            self.restricted_pairs = load(rp_file)
        # Load the unicode translation table
        with open('./unicode_translation_table.json', 'r', encoding='utf-8') \
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
        if message.channel.name not in self.options.get('allowed_channels', []):
            return
        # Translate the message content to avoid wide latin and other spammer tricks
        content = message.content.translate(self.unicode_translation_table)
        # Delete the message if it contains two or more of the monitored words
        detection = detect_world_threshold(message.content, self.restricted_pairs, 2)
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
    # Setup the bot instance
    bot_instance = ModerationBot()
    # Get a token
    token = getenv('IROHA_DISCORD_MODBOT_TOKEN')
    # Start a bot, handle keyboard interrupts
    try:
        bot_instance.loop.run_until_complete( bot_instance.start(token) )
    except KeyboardInterrupt:
        bot_instance.loop.run_until_complete( bot_instance.close() )
    finally:
        bot_instance.loop.close()
