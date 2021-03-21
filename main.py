import discord
import datetime
import os
import pymongo
from pymongo import MongoClient
from decouple import config


client = discord.Client()
cluster = MongoClient(config('MONGO_CONNECTION_URL'))
db = cluster[config('MONGO_DATABASE_NAME')]
collection = db[config('MONGO_USERVOTES_COLLECTION')]
voteChannelId = 822114786204188753


@client.event
async def on_ready():
    print("I live... {0.user}".format(client))


@client.event
async def on_message(message):
    if message.author.id == client.user.id:
        return

    if message.channel.name == 'votes':
        await message.add_reaction("\U0001F44D")
        await message.add_reaction("\U0001F44E")
        await message.add_reaction("\u2753")
        msgDatetime = datetime.datetime.now()
        msgExperationDatetime = msgDatetime + datetime.timedelta(days=3)
        post = {
            'messageId': message.id,
            "messageContent": message.content,
            "authorId": message.author.id,
            "authorName": message.author.name,
            "voteCreatedAt": {
                'year': msgDatetime.year,
                'month': msgDatetime.month,
                'day': msgDatetime.day,
                'hour': msgExperationDatetime.hour,
                'minute': msgDatetime.minute,
            },
            "voteExpireAt": {
                'year': msgExperationDatetime.year,
                'month': msgExperationDatetime.month,
                'day': msgExperationDatetime.day,
                'hour': msgExperationDatetime.hour,
                'minute': msgExperationDatetime.minute,
            },
            "rectionsCount": {
                'thumbsup': 0,
                'thumbsdown': 0,
                'question': 0,
            }
        }
        collection.insert_one(post)
    
    if message.content.startswith('$demprime'):
        if message.content == '$demprime':
            await message.channel.send('If you require assistance, type `$demprime help`.')
        elif message.content == '$demprime help':
            await message.channel.send(
                'De822114786204188753mocracy Prime is online.\n' +
                'All commands can be executed with `$demprime \{argument_here\}` ' +
                'without the curly brackets.'
            )  # if more params are needed I will print out a list of themin this send block
        elif message.content.startswith('$demprime check'):
            msg = str(message.content).split(' ')
            if (len(msg) >= 3):
                username = msg[2]
                print(username)

@client.event
async def on_raw_reaction_add(payload):
    if payload.channel_id != voteChannelId:
        return
    if (payload.emoji.name == '👍'):
        print(str(payload))

client.run(config('TOKEN'))
