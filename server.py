# audio synth
import synth

# random bs
import utils

# user settings
from default_settings import get_default_settings, settings_type
import pickle
from pprint import pformat
DUMP_PATH : str = 'user_settings_table.pickle'
user_settings_table : dict[str, settings_type] = {}
try:
    with open(DUMP_PATH, 'rb') as fp:
        user_settings_table = pickle.load(fp)
except FileNotFoundError:
    pass
def dump_user_settings_table():
    with open(DUMP_PATH, 'wb') as fp:
        pickle.dump(user_settings_table, fp)

# discord.py
import discord

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

# returns (command, args, args_str) upon success
def lexer(content : str):
    args = content.split(' ')
    if args[0] == '-#':
        args.pop(0)
    if '$' not in args[0]:
        raise Exception()
    command = ''.join([c for c in args[0] if c != '$'])
    args_str = ' '.join(args[1:])
    return command, args, args_str

# main server logic
sent_message_cache : dict[int, discord.Message] = {} # keys are user message id's, values are bot replies
async def parse_and_execute(message : discord.Message, command : str, args : list[str], args_str : str):
    # register new users to the user settings table
    user_id = str(message.author.id) # string conversion cuz JSON keys footgun moment
    if user_id not in user_settings_table:
        user_settings_table[user_id] = get_default_settings()
    user_settings = user_settings_table[user_id]

    # ping-reply and cache the reply
    async def reply(content : str | None = None, **kwargs : object):
        sent_message : discord.Message = await message.channel.send(content, **kwargs, reference=message) # type: ignore
        sent_message_cache[message.id] = sent_message

    # edit a previous reply
    async def edit(content : str):
        await sent_message_cache[message.id].edit(content=content)

    # reply and then delete a previous reply
    async def re_reply(content : str | None = None, **kwargs : object):
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
        await reply('https://github.com/Frank-9976/test-bot')
        return

    if command == 'settings':
        await reply(pformat(user_settings))
        return

    if command == 'reset':
        user_settings_table[user_id] = get_default_settings()
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
    if hasattr(user_settings, command_u):
        setting = getattr(user_settings, command_u)

        # $<numerical setting>
        if isinstance(setting, float):
            setattr(user_settings, command_u, utils.parse_num(args[1]))
            await reply(f'set {command_u} to {getattr(user_settings, command_u)}')
        elif isinstance(setting, int):
            setattr(user_settings, command_u, int(args[1]))
            await reply(f'set {command_u} to {getattr(user_settings, command_u)}')

        # $<dictionary setting>
        else:
            
            # $<dictionary setting> [<key 1> <key 2> ...] [<value 1> <value 2> ...]
            if args_str[0] == '[':
                args_str_split = args_str.split('] [')
                keys, values = args_str_split[0][1:].split(' '), args_str_split[1][:-1].split(' ')
                response_message = 'BATCH COMMAND:\n'
                for i in range(len(keys)):
                    key, value = keys[i], values[i]
                    setting[key] = utils.parse_num(value)
                    response_message += f'set {command_u}[{key}] to {setting[key]}\n'
                await reply(response_message[:-1])

            # $<dictionary setting> <key> <value>
            else:
                setting[args[1]] = utils.parse_num(args[2])
                await reply(f'set {command_u}[{args[1]}] to {setting[args[1]]}')

        dump_user_settings_table()
        return

# reply to command edits
@client.event
async def on_message_edit(before : discord.Message, after : discord.Message):
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
    try:
        command, args, args_str = lexer(after.content)
    except Exception:
        return

    # delete old reply and send new one
    await sent_message_cache[after.id].delete()
    await parse_and_execute(after, command, args, args_str)

# reply to commands
@client.event
async def on_message(message : discord.Message):
    # no self-replies
    if message.author == client.user:
        return

    # lexing
    try:
        command, args, args_str = lexer(message.content)
    except Exception:
        return

    # do everything else
    await parse_and_execute(message, command, args, args_str)

# run the server
with open('token.txt') as fp:
    client.run(fp.read())