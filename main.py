import discord
import datetime
import os
import pymongo
from pymongo import MongoClient
from decouple import config
from user import User


client = discord.Client()
cluster = MongoClient(config('MONGO_CONNECTION_URL'))
db = cluster[config('MONGO_DATABASE_NAME')]
userVotesCollection = db[config('MONGO_USERVOTES_COLLECTION')]
userCollection = db[config('MONGO_USER_COLLECTION')]
voteChannelId = 822114786204188753
adminRole = '<@&822112365595983891>'


@client.event
async def on_ready():
    print("I live... {0.user}".format(client))


@client.event
async def on_message(message):
    if message.author.id == client.user.id:
        return

    voter = User(message.author.name + "#" +
                 message.author.discriminator, message.author.id)
    should_add_or_update_voter(voter)

    if message.channel.name == 'votes':
        await message.add_reaction("\U0001F44D")
        await message.add_reaction("\U0001F44E")
        await message.add_reaction("\u2753")
        msgDatetime = datetime.datetime.now()
        msgExperationDatetime = msgDatetime + datetime.timedelta(days=3)
        post = {
            "messageId": message.id,
            "messageContent": message.content,
            "authorId": message.author.id,
            "authorName": message.author.name,
            "voteCreatedAt": {
                'year': msgDatetime.year,
                'month': msgDatetime.month,
                'day': msgDatetime.day,
                'hour': msgDatetime.hour,
                'minute': msgDatetime.minute,
            },
            "voteExpireAt": {
                'year': msgExperationDatetime.year,
                'month': msgExperationDatetime.month,
                'day': msgExperationDatetime.day,
                'hour': msgExperationDatetime.hour,
                'minute': msgExperationDatetime.minute,
            },
            "reactionCount": {
                'thumbsup': 0,
                'thumbsdown': 0,
                'question': 0,
            },
            "isTerminated": False
        }
        userVotesCollection.insert_one(post)

    if message.content.startswith('$demprime'):
        if message.content == '$demprime':
            await message.channel.send('If you require assistance, type `$demprime help`.')
        elif message.content == '$demprime help':
            await message.channel.send(
                'Democracy Prime is online.\n' +
                'All commands can be executed with `$demprime {argument_here}` ' +
                'without the curly brackets.'
            )  # if more params are needed I will print out a list of themin this send block
        elif message.content.startswith('$demprime check'):
            msg = str(message.content).split(' ')
            if (len(msg) >= 3):
                username = msg[2]
                print(username)


@client.event
async def on_raw_reaction_add(payload):
    if payload.channel_id != voteChannelId or \
            payload.user_id == client.user.id or \
            payload.emoji.name not in ['👍', '👎', '❓']:
        return

    print("User with ID {0}'s add reaction has passed the initial check.".format(
        payload.message_id))

    # Grab vote.
    filterVote = {'messageId': payload.message_id}
    vote = userVotesCollection.find_one(filterVote)
    if vote == None or vote['isTerminated'] == True:
        return

    # Update the user vote counts.
    vote["reactionCount"] = update_count(
        payload.emoji.name, vote['reactionCount'], True)

    server = None
    # Grab "Guild" TODO: MAKE THIS MORE DYNAMIC
    for guild in client.guilds:
        if guild.name == 'decentralizedfriends':
            server = guild
            break

    if server == None:
        print('ERROR: Unable to find server')
        return

    # Grab the overall population of the server.
    totalPopulation = server.member_count - 1

    # Check the pass or fail
    voteState = check_pass_or_fail(vote['reactionCount'], totalPopulation)
    print('voteState: ' + voteState)

    # notify users if pass, fail, or if the vote shou
    if voteState != 'neither':
        channel = None
        resolutions = None
        for curChannel in server.channels:
            if curChannel.name == 'votes':
                channel = curChannel
            if curChannel.name == 'resolutions':
                resolutions = curChannel
        if channel == None:
            print('ERROR: Unable to find channel')
            return
        message = await channel.fetch_message(payload.message_id)
        print('Found poll: ' + message.content)
        vote['isTerminated'] = True
        if voteState == 'pass':
            await resolutions.send(
                'poll: [{0}] by: [{1}] has passed! \nFinal Count: [👍 {2}, 👎 {3}, ❓ {4}] \nTotal Population: {6}\n{5}'.format(
                    vote['messageContent'], message.author.mention, vote['reactionCount']['thumbsup'],
                    vote['reactionCount']['thumbsdown'], vote['reactionCount']['question'], adminRole, str(totalPopulation))
            )
            await message.delete()
        elif voteState == 'fail':
            await resolutions.send(
                'poll: [{0}] by: [{1}] has failed! \nFinal Count: [👍 {2}, 👎 {3}, ❓ {4}] \nTotal Population: {6}\n{5}'.format(
                    vote['messageContent'], message.author.mention, vote['reactionCount']['thumbsup'],
                    vote['reactionCount']['thumbsdown'], vote['reactionCount']['question'], adminRole, str(totalPopulation))
            )
            await message.delete()
        elif voteState == 'admins':
            await resolutions.send(
                'poll: [{0}] by: [{1}] will now be elevated to {5} \nFinal Count: [👍 {2}, 👎 {3}, ❓ {4}]\nTotal Population: {6}'.format(
                    vote['messageContent'], message.author.mention, vote['reactionCount']['thumbsup'],
                    vote['reactionCount']['thumbsdown'], vote['reactionCount']['question'], adminRole, str(totalPopulation))
            )
            await message.delete()

    newValues = {"$set": {
        "reactionCount.thumbsup": vote['reactionCount']['thumbsup'],
        "reactionCount.thumbsdown": vote['reactionCount']['thumbsdown'],
        "reactionCount.question": vote['reactionCount']['question'],
        "isTerminated": vote['isTerminated']
    }}
    userVotesCollection.update_one(filterVote, newValues)


@client.event
async def on_raw_reaction_remove(payload):
    if payload.channel_id != voteChannelId or \
            payload.user_id == client.user.id or \
            payload.emoji.name not in ['👍', '👎', '❓']:
        return

    print("User with ID {0}'s add reaction has passed the initial check.".format(
        payload.message_id))

    # Grab vote.
    filterVote = {'messageId': payload.message_id}
    vote = userVotesCollection.find_one(filterVote)
    if vote == None or vote['isTerminated'] == True:
        return

    # Update the user vote counts.
    vote["reactionCount"] = update_count(
        payload.emoji.name, vote['reactionCount'], False)

    newValues = {"$set": {
        "reactionCount.thumbsup": vote['reactionCount']['thumbsup'],
        "reactionCount.thumbsdown": vote['reactionCount']['thumbsdown'],
        "reactionCount.question": vote['reactionCount']['question']
    }}
    userVotesCollection.update_one(filterVote, newValues)


def update_count(emoji, reactionCount, addOrRemove):
    if emoji == '👍':
        reactionCount['thumbsup'] = (
            1 if addOrRemove == True else -1) + reactionCount['thumbsup']
    elif emoji == '👎':
        reactionCount['thumbsdown'] = (
            1 if addOrRemove == True else -1) + reactionCount['thumbsdown']
    elif emoji == '❓':
        reactionCount['question'] = (
            1 if addOrRemove == True else -1) + reactionCount['question']
    return reactionCount


def check_pass_or_fail(reactionCount, totalPopulation):
    totalVotes = reactionCount['thumbsup'] + \
        reactionCount['thumbsdown'] + reactionCount['question']
    print('totalVotes: ' + str(totalVotes))
    percentageOfTotalVoters = (totalVotes * 100) / totalPopulation
    print('percentageOfTotalVoters: ' + str(percentageOfTotalVoters))

    # Check if we should determine a pass or fail
    if percentageOfTotalVoters >= 60:
        percentageOfUpVotes = (
            reactionCount['thumbsup'] * 100) / totalPopulation
        print('percentageOfUpVotes: ' + str(percentageOfUpVotes))
        percentageOfDownVotes = (
            reactionCount['thumbsdown'] * 100) / totalPopulation
        print('percentageOfDownVotes: ' + str(percentageOfDownVotes))
        percentageOfAbstaining = (
            reactionCount['question'] * 100) / totalPopulation
        print('percentageOfAbstaining: ' + str(percentageOfAbstaining))
        # Check for a possible win or loss
        if percentageOfAbstaining > 60:
            return 'fail'
        elif percentageOfUpVotes >= 50:
            return 'pass'
        elif percentageOfDownVotes >= 50:
            return 'fail'
        elif percentageOfUpVotes >= 40 and percentageOfDownVotes < 40:
            return 'pass'
        elif percentageOfDownVotes >= 40 and percentageOfUpVotes < 40:
            return 'fail'
        elif percentageOfUpVotes >= 40 and percentageOfDownVotes >= 40 and percentageOfDownVotes <= 50 and percentageOfUpVotes <= 50:
            return 'admins'

    return 'neither'


def should_add_or_update_voter(voter):
    filterUser = {"id": voter.id}
    user = userCollection.find_one(filterUser)
    if user == None:
        userCollection.insert_one(voter.get_user())
        return
    foundVoter = User(user['name'], user['id'])
    if voter.name != foundVoter.name:
        userCollection.update_one(filterUser, foundVoter.set_name_in_mongo)


def get_voter(userId):
    filterUser = {"id": userId}
    user = userCollection.find_one(filterUser)
    return User(user['name'], user['id'])


client.run(config('TOKEN'))
