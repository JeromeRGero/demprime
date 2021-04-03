import discord
from discord.ext import tasks
import datetime
import os
import pymongo
from pymongo import MongoClient
from decouple import config
from user import User


intents = discord.Intents.default()
intents.members = True
intents.presences = True
client = discord.Client(intents=intents)
cluster = MongoClient(config('MONGO_CONNECTION_URL'))
db = cluster[config('MONGO_DATABASE_NAME')]
userVotesCollection = db[config('MONGO_USERVOTES_COLLECTION')]
userCollection = db[config('MONGO_USER_COLLECTION')]
pollingChannelId = 822114786204188753
resolutionsChannelId = 826264784549969921
adminRole = '<@&822112365595983891>'
unregisterdVoterRoleId = 826438835839172638


@client.event
async def on_ready():
    print("I live... {0.user}".format(client))
    check_all_polls_for_termination.start()


@tasks.loop(minutes=15)
async def check_all_polls_for_termination():
    print("XXXXXXXXXX-15minLoopSTART-XXXXXXXXXX" + \
        "\ncheck_all_polls_for_termination hit!")
    currentDatetime = datetime.datetime.now()
    print("currentDatetime: {}".format(currentDatetime))
    query = {"voteExpireAt": {"$lt": currentDatetime}}
    results = userVotesCollection.find(query)
    print("Found and Terminating:")
    server = client.guilds[0]
    pollingChannel = server.get_channel(pollingChannelId)
    resolutionsChannel = server.get_channel(resolutionsChannelId)
    totalPopulation = get_total_population(server)
    for poll in results:
        stateOfPoll = check_pass_or_fail(poll["reactionCount"], totalPopulation)
        message = await pollingChannel.fetch_message(poll['messageId'])
        voterReactionList = await get_voter_reaction_list(message)
        resolutionMessageString = ''
        if stateOfPoll == 'pass':
            resolutionMessageString = 'poll: [{0}] by: [{1}] has passed! \nFinal Count: [👍 {2}, 👎 {3}, ❓ {4}] \nTotal Population: {6}\n{5}'.format(
                poll['messageContent'], message.author.mention, poll['reactionCount']['thumbsup'],
                poll['reactionCount']['thumbsdown'], poll['reactionCount']['question'], adminRole, str(totalPopulation))
        elif stateOfPoll == 'admins':
            resolutionMessageString = 'poll: [{0}] by: [{1}] will now be elevated to {5} \nFinal Count: [👍 {2}, 👎 {3}, ❓ {4}]\nTotal Population: {6}'.format(
                poll['messageContent'], message.author.mention, poll['reactionCount']['thumbsup'],
                poll['reactionCount']['thumbsdown'], poll['reactionCount']['question'], adminRole, str(totalPopulation))
        else:
            resolutionMessageString = 'poll: [{0}] by: [{1}] has failed! \nFinal Count: [👍 {2}, 👎 {3}, ❓ {4}] \nTotal Population: {6}\n{5}'.format(
                poll['messageContent'], message.author.mention, poll['reactionCount']['thumbsup'],
                poll['reactionCount']['thumbsdown'], poll['reactionCount']['question'], adminRole, str(totalPopulation))
        for curString in voterReactionList:
            resolutionMessageString += curString
        await resolutionsChannel.send(resolutionMessageString)
        filterPoll = {'messageId': poll["messageId"]}
        userVotesCollection.delete_one(filterPoll)
        await message.delete()
        print(poll)
    print("XXXXXXXXXX-15minLoopEND-XXXXXXXXXX")


@client.event
async def on_message(message):
    if message.author.id == client.user.id:
        return

    voter = User(message.author.name + "#" +
                 message.author.discriminator, message.author.id)
    should_add_or_update_voter(voter)

    if message.channel.id == pollingChannelId:
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
            "voteCreatedAt": msgDatetime,
            "voteExpireAt": msgExperationDatetime,
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
    if payload.channel_id != pollingChannelId or \
            payload.user_id == client.user.id or \
            payload.emoji.name not in ['👍', '👎', '❓']:
        return

    # Grab "Guild" TODO: MAKE THIS MORE DYNAMIC
    server = client.guilds[0]
    currentVoter = await server.fetch_member(payload.user_id)
    pollingChannel = server.get_channel(pollingChannelId)
    resolutionsChannel = server.get_channel(resolutionsChannelId)
    message = await pollingChannel.fetch_message(payload.message_id)

    # TODO: Add a return statment if the message.content does not
    # startswith('Poll:')

    print("#####\nUser: [{}] has added a [{}] \nTo poll [{}].\n#####".format(
        currentVoter.name, payload.emoji.name, message.content))

    # Grab vote from mongo.
    filterPoll = {'messageId': payload.message_id}
    poll = userVotesCollection.find_one(filterPoll)
    if poll == None or poll['isTerminated'] == True:
        return

    # TODO make sure user has not reacted to the the poll yet
    # if they have, remove there vote on poll both from
    # the discord message and on mongo.

    # Update the user vote counts.
    poll["reactionCount"] = update_count(
        payload.emoji.name, poll['reactionCount'], True)

    # Grab the overall population of the server.
    totalPopulation = get_total_population(server)

    # Check the pass or fail
    stateOfPoll = check_pass_or_fail(poll['reactionCount'], totalPopulation)
    print('voteState: ' + stateOfPoll)

    # notify users if pass, fail, or if the vote shou
    if stateOfPoll != 'neither':
        print('Found poll: ' + message.content)
        poll['isTerminated'] = True
        voterReactionList = await get_voter_reaction_list(message)
        resolutionMessageString = ''
        if stateOfPoll == 'pass':
            resolutionMessageString = 'poll: [{0}] by: [{1}] has passed! \nFinal Count: [👍 {2}, 👎 {3}, ❓ {4}] \nTotal Population: {6}\n{5}'.format(
                poll['messageContent'], message.author.mention, poll['reactionCount']['thumbsup'],
                poll['reactionCount']['thumbsdown'], poll['reactionCount']['question'], adminRole, str(totalPopulation))
        elif stateOfPoll == 'fail':
            resolutionMessageString = 'poll: [{0}] by: [{1}] has failed! \nFinal Count: [👍 {2}, 👎 {3}, ❓ {4}] \nTotal Population: {6}\n{5}'.format(
                poll['messageContent'], message.author.mention, poll['reactionCount']['thumbsup'],
                poll['reactionCount']['thumbsdown'], poll['reactionCount']['question'], adminRole, str(totalPopulation))
        elif stateOfPoll == 'admins':
            resolutionMessageString = 'poll: [{0}] by: [{1}] will now be elevated to {5} \nFinal Count: [👍 {2}, 👎 {3}, ❓ {4}]\nTotal Population: {6}'.format(
                poll['messageContent'], message.author.mention, poll['reactionCount']['thumbsup'],
                poll['reactionCount']['thumbsdown'], poll['reactionCount']['question'], adminRole, str(totalPopulation))
        for curString in voterReactionList:
            resolutionMessageString += curString
        await resolutionsChannel.send(resolutionMessageString)
        userVotesCollection.delete_one(filterPoll)
        await message.delete()
    else:
        newValues = {"$set": {
            "reactionCount.thumbsup": poll['reactionCount']['thumbsup'],
            "reactionCount.thumbsdown": poll['reactionCount']['thumbsdown'],
            "reactionCount.question": poll['reactionCount']['question'],
            "isTerminated": poll['isTerminated']
        }}
        userVotesCollection.update_one(filterPoll, newValues)


@client.event
async def on_raw_reaction_remove(payload):
    if payload.channel_id != pollingChannelId or \
            payload.user_id == client.user.id or \
            payload.emoji.name not in ['👍', '👎', '❓']:
        return

    # Grab "Guild" TODO: MAKE THIS MORE DYNAMIC
    server = client.guilds[0]
    currentVoter = await server.fetch_member(payload.user_id)

    print("User {0}'s removal of a reaction has passed the initial check.".format(
        currentVoter.name))

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
    print('before: [👍{} 👎{} ❓{}]'.format(reactionCount['thumbsup'],
          reactionCount['thumbsdown'], reactionCount['question']))
    if emoji == '👍':
        reactionCount['thumbsup'] = (
            1 if addOrRemove == True else -1) + reactionCount['thumbsup']
    elif emoji == '👎':
        reactionCount['thumbsdown'] = (
            1 if addOrRemove == True else -1) + reactionCount['thumbsdown']
    elif emoji == '❓':
        reactionCount['question'] = (
            1 if addOrRemove == True else -1) + reactionCount['question']
    print('after: [👍{} 👎{} ❓{}]'.format(reactionCount['thumbsup'],
          reactionCount['thumbsdown'], reactionCount['question']))
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


def should_add_or_update_voter(frontEndVoter):
    filterUser = {"id": frontEndVoter.id}
    user = userCollection.find_one(filterUser)
    if user == None:
        userCollection.insert_one(frontEndVoter.get_user())
        return
    voterFromDB = User(user['name'], user['id'])
    if frontEndVoter.name != voterFromDB.name:
        userCollection.update_one(filterUser, voterFromDB.set_name_in_mongo)


def get_voter_from_db_by_id(userId):
    filterUser = {"id": userId}
    user = userCollection.find_one(filterUser)
    return User(user['name'], user['id'])


async def get_voter_reaction_list(message):
    # add get voter in here or pass in name and discriminator of reacting voter
    voterReactionList = []
    for reaction in message.reactions:
        async for user in reaction.users():
            if user.name == 'Democracy Prime':
                voterReactionList.append(
                    '\n--------------- User with {}'.format(reaction.emoji))
            else:
                voterReactionList.append('\n{0.name}'.format(user))
    return voterReactionList


def get_total_population(server):
    # For the bot
    exclude = 1
    # excluding all 'illegal' members who wish to not vote on polls
    members = server.members
    for member in members:
        for role in member.roles:
            if role.id == unregisterdVoterRoleId:
                exclude += 1

    # Grab the overall population of the server.
    return server.member_count - exclude

client.run(config('TOKEN'))
