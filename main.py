import discord
import os
from decouple import config

client = discord.Client()

@client.event
async def on_ready():
    print("I live... {0.user}".format(client))


@client.event
async def on_message(message):
    if message.author.id == client.user.id:
        return

    print('The author is {0} with id {1}'.format(message.author.name, message.author.id))

    print("The channel is {0}".format(message.channel.name))

    if message.channel.name == 'votes':
        await message.add_reaction("\U0001F44D")
        await message.add_reaction("\U0001F44E")
        await message.add_reaction("\u2753")

    if message.content.startswith('$demprime'):
        if message.content == '$demprime':
            await message.channel.send('If you require assistance, type `$demprime help`')
        elif message.content == '$demprime help':
            await message.channel.send(
                'Democracy Prime is online.\nAll commands can be executed with `$demprime` \{argument_here\}')


client.run(config('TOKEN'))

