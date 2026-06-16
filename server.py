# audio synth
import synth

# user settings
from copy import deepcopy
from pprint import pformat
import json
DUMP_PATH = 'user_settings_table.json'
user_settings_table = {}
try:
    with open(DUMP_PATH, 'r') as fp:
        user_settings_table = json.load(fp)
except FileNotFoundError:
    pass
def dump_user_settings_table():
    with open(DUMP_PATH, 'w') as fp:
        json.dump(user_settings_table, fp)

# discord.py
import discord
TRIGGER_CHAR = '$'

# set intents
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# on startup
@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    
    # sync slash commands
    #CT = discord.app_commands.CommandTree(client)
    #print(await CT.sync())
    
    await client.change_presence(activity=discord.Game('$help'))

# used to parse fractions as floats
def parse_num(num_str):
    slash_split = num_str.split('/')
    if len(slash_split) == 2:
        return float(slash_split[0]) / float(slash_split[1])
    else:
        return float(num_str)

# for $source
from os import listdir

# returns (command, args, args_str) upon success
# returns (None, None, None) if lacking the trigger
def lexer(content):
    args = content.split(' ')
    if args[0] == '-#':
        args.pop(0)
    if TRIGGER_CHAR not in args[0]:
        return None, None, None
    command = ''.join([c for c in args[0] if c != TRIGGER_CHAR])
    args_str = ' '.join(args[1:])
    return command, args, args_str

# main server logic
async def parse_and_execute(message, command, args, args_str):
    # register new users to the user settings table
    user_id = str(message.author.id) # string conversion cuz JSON keys footgun moment
    if user_id not in user_settings_table:
        user_settings_table[user_id] = deepcopy(synth.defaults)
    user_settings = user_settings_table[user_id]

    # ping-reply and cache the reply
    async def reply(content=None, **kwargs):
        sent_message = await message.channel.send(content, **kwargs, reference=message)
        sent_message_cache[message.id] = sent_message

    # edit a previous reply
    async def edit(content):
        await sent_message_cache[message.id].edit(content=content)

    # reply and then delete a previous reply
    async def re_reply(content=None, **kwargs):
        old_message = sent_message_cache[message.id]
        await reply(content, **kwargs)
        await old_message.delete()

    # parse and execute (for real)
    if command == 'help':
        await reply(file=discord.File('help.txt'))
        return

    if command == 'echo':
        await reply(args_str)
        return

    if command == 'source':
        await reply(files=[discord.File(f) for f in listdir('.') if f[-3:] == '.py'])
        return

    if command == 'settings':
        await reply(pformat(user_settings))
        return

    if command == 'reset':
        user_settings_table[user_id] = deepcopy(synth.defaults)
        await reply('all your settings have been reset :P')
        dump_user_settings_table()
        return

    if command == 'play':
        notes = args[1:] + ['9'] # fade to silence at end
        
        await reply('building waveform...')
        samples = await synth.get_samples(notes, user_settings)
        
        await edit('uploading file...')
        buf = synth.buf_from_samples(samples, user_settings)
        
        await re_reply(file=discord.File(buf, filename=f'{args_str[:512]}.wav')) # filename size limit
        return

    if command == 'noise':
        samples = synth.get_noise_samples(user_settings)
        buf = synth.buf_from_samples(samples, user_settings)
        await reply(file=discord.File(buf, filename='noise.wav'))
        return

    # $<setting>
    command_u = command.upper()
    if command_u in user_settings:
        setting = user_settings[command_u]
        
        # $<numerical setting>
        if isinstance(setting, float):
            user_settings[command_u] = parse_num(args[1])
            await reply(f'set {command_u} to {user_settings[command_u]}')
        elif isinstance(setting, int):
            user_settings[command_u] = int(args[1])
            await reply(f'set {command_u} to {user_settings[command_u]}')

        # $<dictionary setting>
        elif isinstance(setting, dict):
            
            # $<dictionary setting> [<key 1> <key 2> ...] [<value 1> <value 2> ...]
            if args_str[0] == '[':
                args_str_split = args_str.split('] [')
                keys, values = args_str_split[0][1:].split(' '), args_str_split[1][:-1].split(' ')
                response_message = 'BATCH COMMAND:\n'
                for i in range(len(keys)):
                    key, value = keys[i], values[i]
                    setting[key] = parse_num(value)
                    response_message += f'set {command_u}[{key}] to {setting[key]}\n'
                await reply(response_message[:-1])

            # $<dictionary setting> <key> <value>
            else:
                setting[args[1]] = parse_num(args[2])
                await reply(f'set {command_u}[{args[1]}] to {setting[args[1]]}')

        dump_user_settings_table()
        return

# reply to command edits
sent_message_cache = {} # keys are user message id's, values are bot replies
@client.event
async def on_message_edit(before, after):
    # must be in discord.py cache (user messages)
    if not before:
        return

    # must be in bot's message cache (bot messages)
    if after.id not in sent_message_cache:
        return

    # no self-replies
    if before.author == client.user:
        return

    # must change content
    if before.content == after.content:
        return

    # must be a command
    command, args, args_str = lexer(after.content)
    if not command:
        return

    # delete old reply and send new one
    await sent_message_cache[after.id].delete()
    await parse_and_execute(after, command, args, args_str)

# reply to commands
@client.event
async def on_message(message):
    # no self-replies
    if message.author == client.user:
        return

    # lexing
    command, args, args_str = lexer(message.content)
    if not command:
        return

    # do everything else
    await parse_and_execute(message, command, args, args_str)

# python server.py < token.txt
client.run(input())