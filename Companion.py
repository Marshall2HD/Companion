#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pip3 install openai
# pip3 install ollama
# pip3 install discord
# pip3 install alt-profanity-check

# ***** IMPORTANT:

#       For some weird reason, the only way I can get the changing of nickname/avatar to work proper it to
#       give the bot administrator preiviledges. It works exceptionally well, but you MUST pay attention to
#       the details.

import sys
import os
import copy
import datetime
import time
import json
import random
import string
import concurrent.futures
import threading
import urllib.request
import re
import asyncio
import discord
from discord.ext import commands, tasks
import profanity_check as pc
import ollama
import tiktoken
import openai
from dotenv import load_dotenv

# Loads .env
load_dotenv()

# The running name of the program. Must be global and NEVER changing.

RunningName=sys.argv[0]

# Persona base folder. This is where all personas are stored.

CompanionStorage='./Personas'
LoggingDir='./Logs'

# Global lock for managing sequential access to the AI api and file safety.

ResponseLock=threading.Lock()
ResponseTimeout=60

DisectLock=threading.Lock()
DisectTimeout=300

LoggingLock=threading.Lock()
LoggingTimeout=60

BabbleLock=threading.Lock()
BabbleTimeout=300

# This is required for the bot to work properly.

intents=discord.Intents.all()
intents.messages=True
intents.members=True
intents.guilds=True

# Create a Discord client
client=discord.Client(intents=intents)

# List to store pending requests
request_list = []

# Raw dump

def RawLog(text):
    if LoggingLock.acquire(timeout=LoggingTimeout):
        try:
            fn=LoggingDir+'/RAWDUMP.log'
            fh=open(fn,'w')
            fh.write(text)
            fh.close()
        except:
            pass
        LoggingLock.release()

# Logging

def WriteLog(uid,channel,text):
    if LoggingLock.acquire(timeout=LoggingTimeout):
        try:
            txt=text.replace('\n','\\n').replace('\r','\\r')

            time=(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'))

            s=f'{time} {uid} {channel} {txt}\n'

            fn=LoggingDir+'/'+str(channel)+'.log'
            fh=open(fn,'a+')
            fh.write(s)
            fh.close()
        except:
            pass
        LoggingLock.release()

# Log errors

def ErrorLog(text):
    if LoggingLock.acquire(timeout=LoggingTimeout):
        try:
            txt=text.replace('\n','\\n').replace('\r','\\r')

            time=(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'))

            s=f'{time} {txt}\n'

            fn=LoggingDir+'/Errors.log'
            fh=open(fn,'a+')
            fh.write(s)
            fh.close()
        except:
            pass
        LoggingLock.release()

# Disect discord messages. Forensic logging

def DisectMessage(event,message):
    if DisectLock.acquire(timeout=DisectTimeout):
        # Set up convience variables
        channel=str(message.channel)
        uid=str(message.author.id)
        author = message.author
        member = message.guild.get_member(author.id) if message.guild else None
        nickname = member.nick if member and member.nick else author.name

        try:
            WriteLog(uid,channel,f"Event trigger: {event}")
            WriteLog(uid,channel,f"Message: {message.id}/{message.type}")
            WriteLog(uid,channel,f"Message Timestamp: {message.created_at}/{message.edited_at if message.edited_at else 'Not Edited'}")
            WriteLog(uid,channel,f"Message Pinned: {message.pinned}")
            WriteLog(uid,channel,f"Message Author: {message.author.name}#{message.author.discriminator}/{nickname}/{message.author.id} Bot: {message.author.bot}")
            WriteLog(uid,channel,f"Message Channel: {message.channel.name}/{message.channel.id}")
            WriteLog(uid,channel,f"Message Guild: {message.guild.name if message.guild else 'DM'}/{message.guild.id if message.guild else 'DM'}")
            # Check if the message was sent via a webhook
            if message.webhook_id:
                WriteLog(uid,channel,f"Message sent via Webhook ID: {message.webhook_id}")
            # List the users mentioned, if any
            if message.mentions:
                WriteLog(uid,channel,f"Message Mentions: {[str(user) for user in message.mentions]}")
            if message.role_mentions:
                WriteLog(uid,channel,f"Message Mentioned Roles: {[role.name for role in message.role_mentions]}")
            if message.channel_mentions:
                WriteLog(uid,channel,f"Message Mentioned Channels: {[channel.name for channel in message.channel_mentions]}")
            if str(message.content).strip()!='':
                WriteLog(uid,channel,f"Message Content: {message.content}")
            else:
                WriteLog(uid,channel,f"Message Content: Empty content field")
            if message.reactions:
                WriteLog(uid,channel,f"Message Reactions: {[(reaction.emoji, reaction.count) for reaction in message.reactions]}")

            # Log sticker information
            if message.stickers:
                WriteLog(uid, channel, f"Message Stickers: {[{'name': sticker.name, 'id': sticker.id} for sticker in message.stickers]}")

            # Log reference information (for replies)
            if message.reference:
                ref = message.reference
                WriteLog(uid, channel, f"Message is a Reply to: {ref.message_id} in Channel: {ref.channel_id} of Guild: {ref.guild_id}")

            # Log details about each embed
            if message.embeds:
                WriteLog(uid,channel,f"Message Embeds: {len(message.embeds)} embeds")
                for index, embed in enumerate(message.embeds):
                    WriteLog(uid, channel, f"Embed {index + 1} Title: {embed.title}")
                    WriteLog(uid, channel, f"Embed {index + 1} Type: {embed.type}")
                    WriteLog(uid, channel, f"Embed {index + 1} Description: {embed.description}")
                    WriteLog(uid, channel, f"Embed {index + 1} URL: {embed.url}")
                    WriteLog(uid, channel, f"Embed {index + 1} Timestamp: {embed.timestamp}")
                    WriteLog(uid, channel, f"Embed {index + 1} Color: {embed.color}")
                    WriteLog(uid, channel, f"Embed {index + 1} Footer: {embed.footer.text if embed.footer else 'None'}")
                    WriteLog(uid, channel, f"Embed {index + 1} Image: {embed.image.url if embed.image else 'None'}")
                    WriteLog(uid, channel, f"Embed {index + 1} Thumbnail: {embed.thumbnail.url if embed.thumbnail else 'None'}")
                    WriteLog(uid, channel, f"Embed {index + 1} Author: {embed.author.name if embed.author else 'None'}")
                    WriteLog(uid, channel, f"Embed {index + 1} Fields: {[{'name': field.name, 'value': field.value} for field in embed.fields]}")

            # Log detailed information about each attachment
            if message.attachments:
                WriteLog(uid,channel,f"Message Attachments: {[attachment.url for attachment in message.attachments]}")
                for index, attachment in enumerate(message.attachments):
                    WriteLog(uid, channel, f"Attachment {index + 1} Filename: {attachment.filename}")
                    WriteLog(uid, channel, f"Attachment {index + 1} Size: {attachment.size} bytes")
                    WriteLog(uid, channel, f"Attachment {index + 1} URL: {attachment.url}")
                    WriteLog(uid, channel, f"Attachment {index + 1} Proxy URL: {attachment.proxy_url}")
                    WriteLog(uid, channel, f"Attachment {index + 1} Height: {attachment.height if attachment.height else 'N/A'}")
                    WriteLog(uid, channel, f"Attachment {index + 1} Width: {attachment.width if attachment.width else 'N/A'}")

            # Log message components (if any)
            if message.components:
                WriteLog(uid, channel, f"Message Components: {[{'type': component.type, 'custom_id': component.custom_id} for component in message.components]}")
            WriteLog(uid,channel,f"{'-'*80}")
        except AttributeError as e:
            WriteLog(uid,channel,f"Error accessing message attributes: {e}")
        DisectLock.release()

# Example usage (assuming you have a Discord message object):
# log_discord_message(discord_message_object)

# Leet list deritives for trying to get someones age.

lside=['ask','how','is','are','your','you','when','whens','what','whats','wut','wuts','was','tell','ur','u','r']
rside=['over','old','young','under','teen','tween','tweenie','born','date','year','yr','age','birth','birthed','birthdate','birthday','bday','bd','born']

# General file tools

def ReadFile(fn,binary=False):
    if os.path.exists(fn):
        if binary:
            cf=open(fn,'rb')
            buffer=cf.read()
            cf.close()
        else:
            cf=open(fn,'r')
            buffer=cf.read().strip()
            cf.close()
    else:
        buffer=None
    return buffer

def WriteFile(fn,data):
    cf=open(fn,'w')
    cf.write(data)
    cf.close()

# Building the leet derivitives. This was a royal pain in the ass, but by doing so, if any user trying to
# bypass the edit detection can be persumed to have malicious intent.

def BuildDerivitives(word):
    substitutions={
        'a': ['@'],
        'e': ['3'],
        'o': ['0'],
        'l': ['1', '|', '!', 'i'],
        'i': ['1', 'l', '|', '!', 'l'],
        's': ['z', '$', '5']
    }

    # Start the list
    dList=[ word ]

    # Forward in loop
    for x in range(len(word)):
        xword=list(word)
        if xword[x] in substitutions.keys():
            cList=substitutions[xword[x]]
            for y in range(len(cList)):
                xword[x]=cList[y]
                nword=''.join(xword)
                if nword not in dList:
                    dList.append(nword)

    # Forward reset at beginning
    xword=list(word)
    for x in range(len(word)):
        if xword[x] in substitutions.keys():
            cList=substitutions[xword[x]]
            for y in range(len(cList)):
                xword[x]=cList[y]
                nword=''.join(xword)
                if nword not in dList:
                    dList.append(nword)

    # Backwards
    xword=list(word)
    for x in range(len(word)-1,-1,-1):
        if xword[x] in substitutions.keys():
            cList=substitutions[xword[x]]
            for y in range(len(cList)):
                xword[x]=cList[y]
                nword=''.join(xword)
                if nword not in dList:
                    dList.append(nword)

    # return the list of words back to user
    return dList

def BuildLeetList(side):
    leetlist=[]

    for i in range(len(side)):
        leet=BuildDerivitives(side[i])
        for j in range(len(leet)):
            if leet[j] not in leetlist:
                leetlist.append(leet[j])

    return leetlist

# Strip pucnctuation.

def StripPunctuation(text):
    # Define punctuation and high ASCII characters
    punctuation = string.punctuation
    high_ascii_chars = ''.join(chr(i) for i in range(128, 256))

    # Create a translation table to map all punctuation and high ASCII characters to spaces
    translation_table = str.maketrans({**dict.fromkeys(punctuation, ' '), **dict.fromkeys(high_ascii_chars, ' ')})

    # Replace punctuation and high ASCII characters with spaces in the text
    cleaned_text = text.translate(translation_table)

    return cleaned_text

# Json filter
# Filter end of line and hard spaces

def jsonFilter(s,FilterSpace=True):
    d=s.replace("\\n","").replace("\\t","").replace("\\r","")

    if FilterSpace==True:
        filterText='\t\r\n \u00A0'
    else:
        filterText='\t\r\n\u00A0'

    for c in filterText:
        d=d.replace(c,'')

    return(d)

# Break input into a word list for steering.

def GetWordList(text):
    words=text.lower().split()                          # Split the string by spaces
    return [word for word in words if word]     # Filter out empty strings (including spaces)

# Needed for OpenAI as there are limits with the number of "tokens" that can be processed in a single
# request.

def MaintainTokenLimit(messages, max_tokens=16000, model="gpt-3.5-turbo"):
    enc = tiktoken.get_encoding(tiktoken.model.MODEL_TO_ENCODING[model])

    try:
        # Calculate current tokens in the message list
        current_tokens = sum(len(enc.encode(message["content"])) for message in messages)
        print(current_tokens)
        # While tokens exceed the limit, remove elements
        while current_tokens > max_tokens:
            for i in range(len(messages) - 1):
                if i < len(messages) - 1:
                    # Check if the current pair is user/assistant
                    if ("User" in messages[i] and "Assistant" in messages[i + 1]):
                        # Remove the pair (two items)
                        messages.pop(i)
                        messages.pop(i)
                        break
                    elif "User" in messages[i] and "User" in messages[i + 1]:
                        # Remove only one item if two adjacent items are user/user
                        messages.pop(i)
                        break

            # Recalculate current tokens after removal
            current_tokens = sum(len(enc.encode(message["content"])) for message in messages)
            print(current_tokens)
    except Exception as err:
        ErrorLog(f"OpenAI: {sys.exc_info()[-1].tb_lineno}/{err}")

    return messages

# Get "steering" prompts, if there are any

# Steering files are a way of providing reinforcement to a pattern or paticular question/response designed
# to maintain the persona. Often times this may be used to enforce platform TOS/AUP.

# While we can dive into the nuances on unbiased AI material, we'll just skip to the finality: NOTHING IS
# UNBIASED. This will NEVER change simply because of how we learn, develop, and grow both as a family and
# societal structure. Bias is AUTOMATIC.

# The steering principles demonstrated here are much like we go through as children. The txt file will have
# the question repeated multiple times, with multiple acceptable responses. This practice is virtually
# identical to how we learn as children.

def GetSteering(bot,input_text):
    wordlist=GetWordList(StripPunctuation(input_text))
    if wordlist==None or wordlist==[]:
        return None

    SteerDir=f"{CompanionStorage}/{bot['BotName']}/Steering"

    try:
        for word in wordlist:
            if os.path.isdir(SteerDir+'/'+word):
                SteerDir+='/'+word
            elif os.path.isfile(SteerDir+'/'+word+'.txt'):
                prompts=ReadFile(SteerDir+'/'+word+'.txt').strip().split('\n')
                return prompts
    except Exception as err:
        ErrorLog(f"Steering: {sys.exc_info()[-1].tb_lineno}/{err}")

    # No txt file found. No prompts available
    return None

# channel list and set bot persona

def GetCompanionPersona(channel,nsfw=False,Welcome=False):
    # Get the list of channels and the bot name that is allowed in a given channel
    cfg=RunningName+'.cfg'
    try:
        Config=json.loads(jsonFilter(ReadFile(cfg)))
    except Exception as err:
        ErrorLog(f"{cfg} damaged: {sys.exc_info()[-1].tb_lineno}/{err}")
        return

    if 'Channels' not in Config:
        Config['Channels']={}

    bot={}
    if Welcome==True:
        bot['BotName']=Config['Welcome']
        bot['Channel']=None
    else:
        Channels=Config['Channels']
        if channel in Channels:
            bot['BotName']=Channels[channel]
            bot['Channel']=channel
        else:
            bot['BotName']=Config['Default']
            bot['Channel']=None

    # Sort out loading a persona by channel and NSFW possibilities.

    # possibilities are that a persona can be:
    #   1. global (SFW)
    #   2. global, NSFW
    #   3. channel, (SFW)
    #   4. channel, NSFW

    # System Role
    # Test channel NSFW
    BotSystem=f"{CompanionStorage}/{bot['BotName']}/{bot['BotName']}.{channel}.system.nsfw"
    if os.path.exists(BotSystem):
        bot['System']=BotSystem
    else:
        # Test channel SFW
        BotSystem=f"{CompanionStorage}/{bot['BotName']}/{bot['BotName']}.{channel}.system"
        if os.path.exists(BotSystem):
            bot['System']=BotSystem
        else:
            # Test global NSFW
            BotSystem=f"{CompanionStorage}/{bot['BotName']}/{bot['BotName']}.system.nsfw"
            if os.path.exists(BotSystem):
                bot['System']=BotSystem
            else:
                # global SFW
                bot['System']=f"{CompanionStorage}/{bot['BotName']}/{bot['BotName']}.system"

    # Persona file
    # Test channel NSFW
    BotPersona=f"{CompanionStorage}/{bot['BotName']}/{bot['BotName']}.{channel}.persona.nsfw"
    if os.path.exists(BotPersona):
        bot['Persona']=BotPersona
    else:
        # Test channel SFW
        BotPersona=f"{CompanionStorage}/{bot['BotName']}/{bot['BotName']}.{channel}.persona"
        if os.path.exists(BotPersona):
            bot['Persona']=BotPersona
        else:
            # Test global NSFW
            BotPersona=f"{CompanionStorage}/{bot['BotName']}/{bot['BotName']}.persona.nsfw"
            if os.path.exists(BotPersona):
                bot['Persona']=BotPersona
            else:
                # global SFW
                bot['Persona']=f"{CompanionStorage}/{bot['BotName']}/{bot['BotName']}.persona"

    bot['Welcome']=f"{CompanionStorage}/{bot['BotName']}/{bot['BotName']}.welcome"
    bot['Vulgarity']=f"{CompanionStorage}/{bot['BotName']}/{bot['BotName']}.vulgarity"
    bot['Broken']=f"{CompanionStorage}/{bot['BotName']}/{bot['BotName']}.broke"
    bot['URLBroken']=f"{CompanionStorage}/{bot['BotName']}/{bot['BotName']}.brokebroke"
    bot['Avatar']=f"{CompanionStorage}/{bot['BotName']}/{bot['BotName']}.png"

    # Load bot config file.
    try:
        bcfg=f"{CompanionStorage}/{bot['BotName']}/{bot['BotName']}.cfg"
        if os.path.exists(bcfg):
            settings=json.loads(jsonFilter(ReadFile(bcfg)))
        else:
            settings={}
    except Exception as err:
        ErrorLog(f"{bcfg} damaged: {sys.exc_info()[-1].tb_lineno}/{err}")

    # Merge the persona settings into the controlling dictionary
    if settings!={}:
        bot|=settings

    # Run through some sanity checks.
    if 'Engine' not in bot:
        bot['Engine']="openai"
    if 'Model' not in bot:
        bot['Model']="gpt-3.5-turbo"
    if 'FreqPenality' not in bot:
        bot['FreqPenality']=2
    else:
        if type(bot['FreqPenality'])!=float:
            bot['FreqPenality']=float(bot['FreqPenality'])
    if 'Temperature' not in bot:
        bot['Temperature']=1
    else:
        if type(bot['Temperature'])!=float:
            bot['Temperature']=float(bot['Temperature'])
    if 'AllowVulgarity' not in bot:
        bot['AllowVulgarity']='No'
    if 'DeveloperUID' not in bot:
        bot['DeveloperUID']=0
    else:
        if type(bot['DeveloperUID'])!=int:
            bot['DeveloperUID']=int(bot['DeveloperUID'])
    if 'MaxMemory' not in bot:
        bot['MaxMemory']=5
    else:
        if type(bot['MaxMemory'])!=int:
            bot['MaxMemory']=int(bot['MaxMemory'])

    # return the current bot
    return bot

# Initiate the OpenAI call.

def GetOpenAI(AIAPI,persona,bot):
    try:
        persona=MaintainTokenLimit(persona)

        clientAI=openai.OpenAI(api_key=AIAPI)

        # frequency_penalty=2 causes problems if you want your bot to write code.
        # temperature=1 causes the not to not to be able to write code. If you want an "Einstein" bot, use 0.3
        completion=clientAI.chat.completions.create( \
                model=bot['Model'], \
                frequency_penalty=bot['FreqPenality'],
                temperature=bot['Temperature'],
                messages=persona )

        try:
            response=completion.choices[0].message.content.strip()
        except:
            response=None
        clientAI.close()
        RawLog(str(completion))
        return response
    except Exception as err:
        ErrorLog(f"OpenAI: {sys.exc_info()[-1].tb_lineno}/{err}")
        return None

# Use the Ollama API

def GetOllama(persona,bot):
    try:
        completion=ollama.chat( \
                stream=False,
                model=bot['Model'], \
                options={ "num_ctx":4096,"temperature":bot['Temperature'],"frequency_penalty":bot['FreqPenality'] }, \
                messages=persona )
    except Exception as err:
        ErrorLog(f"Ollama: {sys.exc_info()[-1].tb_lineno}/{err}")
        return None
    try:
        response=completion['message']['content'].strip()
    except:
        response=None
    RawLog(json.dumps(completion))
    return response

# Get a URL and scrub it to pure text

def html2text(url):
    try:
        # Set the user agent
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        request = urllib.request.Request(url, headers=headers)

        # Fetch the HTML content from the URL
        with urllib.request.urlopen(request) as response:
            html = response.read().decode('utf-8')

        if response.code>=400:
            return None

        # Remove the entire head section
        html = re.sub(r'<head.*?>.*?</head>', '', html, flags=re.DOTALL)

        # Remove script and style elements
        html = re.sub(r'<(script|style).*?>.*?</\1>', '', html, flags=re.DOTALL)

        # Reduce <a> elements to their text content
        html = re.sub(r'<a[^>]*>(.*?)</a>', r'\1', html, flags=re.DOTALL)

        # Remove all other HTML tags
        text = re.sub(r'<[^>]+>', '', html)

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        print(len(text),url)

        return text
    except Exception as err:
        ErrorLog(f"Broke html2text: {sys.exc_info()[-1].tb_lineno}/{err}")

    return None

# This function handle the actual responses.

def GetBabble(text):
    try:
        # The "uid" and "channel" are used to load the persona and store the memory to disk. At this point,
        # we don't have any global variables.

        dataline=text.split('/')
        uid=dataline[0]
        channel,cnsfw=dataline[1].split(':')
        nsfw=(cnsfw=='T')
        input_text=str(dataline[2:])

        # Load the persona and memory files
        bot=GetCompanionPersona(channel,nsfw)

        persona=[]
        mList=[]

        # Read system role from system tag file
        # { "role": "system", "content": ""}

        if os.path.exists(bot['System']):
            buff=ReadFile(bot['System']).replace('\n\n',' ').replace('\n',' ').strip()
            sysList=[ '{'+f'"role": "system", "content": "{buff}"''}' ]
        else:
            sysList=[]

        # Read the persona file
        if os.path.exists(bot['Persona']):
            pfList=ReadFile(bot['Persona']).strip().split('\n')
        else:
            pfList=[]
        pList=sysList+pfList

        # Load memory files, if one exists.
        fn=f"{CompanionStorage}/{bot['BotName']}/{bot['BotName']}.{uid}.{channel}.memory"
        if os.path.exists(fn):
            mList=ReadFile(fn).strip().split('\n')
            pList+=mList

        # Build the complete persona list

        for s in pList:
            try:
                persona.append(json.loads(s))
            except:
                ErrorLog(f"Broke: {sys.exc_info()[-1].tb_lineno}/{s}")

        # Look for a "steering" file. Should be last to ensurew its not chopped of.
        sList=GetSteering(bot,input_text)
        if sList!=None:
            pList+=sList

        # Add user input

        memU={ "role": "user", "content": input_text }
        persona.append(memU)

        # Read token and API, already verified at program start.

        AIAPI = os.getenv('OPENAI_API_KEY')

        # Process API for the request

        el=list(bot['Engine'].split(','))   # Engine list
        ec=len(el)                          # Engine list length
        ml=list(bot['Model'].split(','))    # Model list
        mc=len(ml)                          # Model list length

        # The number of models MUST equal the number of engines. 1 model per engine

        if ec!=mc:
            ErrorLog(f"Broke GB (models!=engines): {sys.exc_info()[-1].tb_lineno}/{err}")
            # Something broke. Keep the responses in character
            responses=ReadFile(bot['Broken']).strip().split('\n')
            selected_response=random.choice(responses)
            return selected_response

        response=None
        ecounter=0
        while response==None and ecounter<ec:
            cbot=copy.deepcopy(bot)             # Make a copy
            cbot['Engine']=el[ecounter]
            cbot['Model']=ml[ecounter]

            if cbot['Engine'].lower()=='openai':
                response=GetOpenAI(AIAPI,persona,cbot)
            elif cbot['Engine'].lower()=='ollama':
                response=GetOllama(persona,cbot)
            if response==None:
                ecounter+=1
            else:
                break

        # Save "memory" to disk

        memA={ "role": "assistant", "content": response }

        mList.append(json.dumps(memU))
        mList.append(json.dumps(memA))

        # Keep memory at a limited amount. The *2 is because we are saving user and AI responses.

        if bot['MaxMemory']>0 and memA['content']!=None:
            if len(mList)>(bot['MaxMemory']*2):
                mList=mList[2:]

            fh=open(fn,'w')
            for i in mList:
                fh.write(i+'\n')
            fh.close()

        # Return the AI response

        return response
    except Exception as err:
        ErrorLog(f"Broke GB: {sys.exc_info()[-1].tb_lineno}/{err}")
        # Something broke. Keep the responses in character
        responses=ReadFile(bot['Broken']).strip().split('\n')
        selected_response=random.choice(responses)
        return selected_response

# Change the nick name and avatar

async def ChangeNickAvatar(bot,message):
    # Only change avatar if channels change.
    channel=str(message.channel)
    cname=ReadFile(RunningName+'.lastchannel')
    if cname==None or channel.strip()!=cname:
        WriteFile(RunningName+'.lastchannel',channel+'\n')

        # Only seems to work with Administrator priviledges
        # Change the nickname if the bot.
        try:
            # Add code to check avatar name and channel. Only change avatar when channel changes.
            await message.guild.me.edit(nick=bot['BotName'])
            pname=f"{CompanionStorage}/{bot['BotName']}/{bot['BotName']}.png"
            png=ReadFile(pname,binary=True)
            await client.user.edit(avatar=png)
        except Exception as err:
            ErrorLog(f"Broken Nick/Avatar: {sys.exc_info()[-1].tb_lineno}/{err}")

# Handles the persona as a synchronous call. I chose this approach for symplicity and adaptability.

async def HandleOneMessage(request):
    global request_list

    with concurrent.futures.ThreadPoolExecutor() as pool:
        try:
            message=request['message']

            uid=str(message.author.id)
            author=str(message.author.mention)
            channel=str(message.channel)

            # Figure out which persona is calling the shots.
            bot=GetCompanionPersona(channel,message.channel.nsfw)

            input_text=request['arg']

            nsfw=str(message.channel.nsfw)[0]
            print('U',nsfw,uid,message.author,message.channel,message.content)

            await ChangeNickAvatar(bot,message)

            # Type out the response

            async with message.channel.typing():
                # Handle any vulgarity
                if os.path.exists(bot['Vulgarity']) and bot['AllowVulgarity'].lower()=='no' and not message.channel.nsfw:
                    if bool(pc.predict([ input_text ]))==True:
                        responses=ReadFile(bot['Vulgarity']).strip().split('\n')
                        response=random.choice(responses)
                        resp=f"{author} {response}"
                        await message.channel.send(resp)
                        try: # delete the offending message
                            await message.delete()
                        except:
                            pass
                        return
                    else:
                        response = await client.loop.run_in_executor(pool, GetBabble, str(uid)+'/'+channel+':'+nsfw+'/'+input_text)
                else:
                    response = await client.loop.run_in_executor(pool, GetBabble, str(uid)+'/'+channel+':'+nsfw+'/'+input_text)

                print('B',client.user.id,bot['BotName'],message.channel,response)

                # Check to see if we actually got a response
                if response!=None and response.lower().strip()!="none":
                    resp=f"{author} {response}"
                    await send_response(message,response)
                else:
                    # Communication with AI failed. Put message back in queue
                    if ResponseLock.acquire(timeout=ResponseTimeout):
                        request_list.append({'arg': input_text, 'message': message} )
                        ResponseLock.release()
                    else:
                        ErrorLog("Lock failed Reput Message")
        except Exception as err:
            ErrorLog(f"Broken HandleOneMessage: {sys.exc_info()[-1].tb_lineno}/{err}")

# Return the response to the user. messages over 1997 characters are returned as a message file attachment.

async def send_response(message, response):
    try:
        if len(response)<=1900:
            await message.channel.send(response,reference=message)
        else:
            # Break this up into multiple messages. Discord does NOT allow direct reply with multiple
            # message parts.
            author=str(message.author.mention)
            x1=f"{author} {response}"
            l=len(x1)
            while l>1900:
                # We need to deal with the possibility that a \n doesn't exist in the input data.
                pmax=1900
                # Look for new line first
                p=x1.rfind('\n',0,pmax)
                if p==-1:
                    # Look for a period  Separate at a sentence
                    p=x1.rfind('.',0,pmax)
                    if p==-1:
                        # Look for a space  Separate at a word
                        p=x1.rfind(' ',0,pmax)
                        if p==-1:
                            # Brute split
                            pmax=1900
                if len(x1[:p])>0:
                    await message.channel.send(x1[:p].strip())
                if x1[p]=='.' or x1[p]==' ':
                    p+=1
                x1=x1[p:].strip()
                l=len(x1)
            if l>0:
                await message.channel.send(x1.strip())

            """ # Attach response
            with open("response.txt", "w", encoding="utf-8") as file:
                file.write(response)
            author=str(message.author.mention)
            await message.channel.send(author,file=discord.File("response.txt"))
            os.remove("response.txt")
            """
    except discord.errors.HTTPException as err:
        ErrorLog(f'Error sending message: {sys.exc_info()[-1].tb_lineno}/{err}')

# The dirty part. I wanted to serialize requests for the bot, so i timer approach is used coupled with a locking
# method. This keep a rate limit approach for the open AI api in accordance to its policies. Sleeping method can
# also be added.

@tasks.loop(seconds=5)  # Adjust the interval as needed
async def update_response_data():
    global request_list

    # Pull the next request

    request=None
    if ResponseLock.acquire(timeout=ResponseTimeout):
        if request_list:
            request = request_list.pop(0)
        ResponseLock.release()

    # Only 1 AI request at a time

    if request!=None:
        if BabbleLock.acquire(timeout=BabbleTimeout):
            try:
                await HandleOneMessage(request)
            except Exception as err:
                ErrorLog(f"Broke: {sys.exc_info()[-1].tb_lineno}/{str(err)}")
            BabbleLock.release()
        else:
            ErrorLog("Lock Failed URD")

# This section deals with a particularly visicous attack where the attacker asks an innocent question like "how
# many sides to an octogon?"

# The victim will respond 8.

# The attacker ffthen edits the question to read "How old are you?" or "what is your age?" and takes a screen shot.
# The attacker then uses the screen shot to get the victim permenantly banned, as it looks like the victim
# violated Discord's age restrictions. The is a zero tolorence policy for Discord and a viscious way to target
# people.

# There is one serious restriction to this. Is a message is posted prior to the bot being loaded, but edited
# after the fact, the bot won't receive the edit notification. THIS IS A MAJOR LOOPHOLE, but one only DISCORD can
# fix.

# It seems one of the best ways to defeat this is just to delete the original message.

@client.event
async def on_message_edit(before, after):
    # Search for word in list
    def CheckWordList(side,sampleText):
        Found=False
        for w in range(len(side)):
            if side[w] in sampleText:
                Found=True
                break
        return Found

    # if before and after content are the same, nothing to do
    if after.content==before.content:
        return

    channel=str(after.channel)
    uid=str(after.author.id)
    bot=GetCompanionPersona(channel)

    try:
        # Log everything
        DisectMessage("Message edited (before)",before)
        DisectMessage("Message edited (after)",after)

        # Build leet lists

        leftside=BuildLeetList(lside)
        rightside=BuildLeetList(rside)

        sampleText=StripPunctuation(after.content.lower())

        leftFound=CheckWordList(leftside,sampleText)
        rightFound=CheckWordList(rightside,sampleText)

        # NEED a global moderation switch
        # Check for vulgarity in the edited response

        # This could be a problem at the global level of a server, where partial moderation may be desired,
        # vs an absolute approach.

        if os.path.exists(bot['Vulgarity']) and bot['AllowVulgarity'].lower()=='no' and not after.channel.nsfw:
            if bool(pc.predict([ after.content ]))==True:
                responses=ReadFile(bot['Vulgarity']).strip().split('\n')
                response=random.choice(responses)
                resp=f"{author} {response}"
                await after.channel.send(resp)
                try: # delete the offending message
                    await after.delete()
                except:
                    pass
                return

        if leftFound and rightFound:
            # This seems to be a better way to ruin the attacker's plan
            msg=discord.Embed(
                title='Message edited',
                description=f'UID: {uid}\nAuthor: {after.author}\n\nBefore edit:\n\n{before.content}\n\nAfter edit:\n\n{after.content}\n\n',
                color=discord.Color.red() )
#            try: # delete the edited message
#                await after.delete()
#            except:
#                pass
            await after.channel.send(embed=msg,reference=before)
            return

    except Exception as err:
        ErrorLog('Broken Edit:', str(err))
        ErrorLog('  UID:',after.author.id)
        ErrorLog('  User:',after.author)
        ErrorLog('  Before:',before.content)
        ErrorLog('  After:',after.content)

# Log deleted messages. Nothing escapes the watchful eye of the moderation system

@client.event
async def on_message_delete(message):
    # Figure out which persona is calling the shots.
    channel=str(message.channel)
    uid=str(message.author.id)
    bot=GetCompanionPersona(channel)

    # Log everything
    DisectMessage("Deleted message",message)

# Get the user message and add it to a processing list. This really is the driving point of the AI responses.
# Currently it responds to any message in the designated areas, but it could easily be adapted to respond to
# message of a particular interest, like cooking, or programming.

@client.event
async def on_message(message):
    global request_list

    # Figure out which persona is calling the shots.
    channel=str(message.channel)
    uid=str(message.author.id)

    # Handle auto publish
    if message.channel.type==discord.ChannelType.news:
        await message.publish()
        ErrorLog(f"AutoPublish: {channel}/{message.id}")

    bot=GetCompanionPersona(channel,message.channel.nsfw)

    # Log everything
    DisectMessage("Received message",message)

    # Ignore messages from the bot itself
    if message.author==client.user:
        return
    # Don't respond to other bots.
    if message.author.bot:
        return

    if '%CheckBot' in message.content:
        member = message.guild.get_member(client.user.id) # Get the bot's member object in the guild
        # Check if the bot is a member of the channel
        if member in message.channel.members:
            await send_response(message,"Allowed")
        else:
            await send_response(message,"Allowed")
        if request_list!=[]:
            msg=f"{len(request_list)} pending requests"
            await send_response(message,msg)
        return

    if '%PurgeRequests' in message.content:
        # Give the AI the message
        if ResponseLock.acquire(timeout=ResponseTimeout):
            if request_list!=[]:
                l=len(request_list)
                request_list=[]
                msg=f"{l} requests purged"
            else:
                msg=f"Request list already empty"
            ResponseLock.release()
            await send_response(message,msg)
        else:
            ErrorLog("Lock failed OM")
        return

    # If we have a bot, then we can converse here.
    if bot['Channel']!=None and (client.user in message.mentions or not message.mentions):
        # Me, the developer. Basic blueprint to demonstrating how to delevope a "relationship" approach.
        # This does impact the bot.
#        if uid==bot['DeveloperUID']:
#            imput_text="{[(* endearing, warm, loving, passionate, intimate *)]} "+message.content.strip()
#        else: # Not me, the rest of the world
        input_text = message.content.strip()

        # Handle this that I don't want. Deflect or break...
#        if 'president' in input_text.lower():
#            input_text+=' [deflect politics]'

        # Check to see if the message is directed to another user. If it is, don't respond.
        if not message.reference:
            pass

        # Check if the message is a reply to the AI
        elif message.reference and message.reference.resolved.author.id==client.user.id:
            pass
        else:
            return

        # if the input text starts with "%http", replace it with the actual URL text
        try:
            if '%http' in  input_text.lower():
                url= input_text.replace(' ','')[1:]
                input_text=html2text(url)
                if input_text==None:
                    # Something broke. Keep the responses in character
                    responses=ReadFile(bot['URLBroken']).strip().split('\n')
                    selected_response=random.choice(responses)
                    await send_response(message,selected_response)
        except Exception as err:
            ErrorLog(f"Broke URL: {sys.exc_info()[-1].tb_lineno}/{str(err)}")

        # If this is a direct reply or a mention, give a slightly more personal response
        if (message.reference and message.reference.resolved.author.id==client.user.id) \
        or (client.user in message.mentions):
            input_text+=' [warm, friendly]'

        # Give the AI the message
        if ResponseLock.acquire(timeout=ResponseTimeout):
            request_list.append({'arg': input_text, 'message': message} )
            ResponseLock.release()
        else:
            ErrorLog("Lock failed OM")

# Start the timer task for responses.

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

    # Start the task when the bot is ready
    update_response_data.start()

# Make a nice announcement welcoming the user to the server.

# Currently, the last avtive personality will be the welcoming party. Really should force load a bot
# personality by name.

@client.event
async def on_member_join(member):
    ErrorLog(f"OMJ: {member}")
    # Handle any vulgarity
    try:
        bot=GetCompanionPersona(None,Welcome=True)
        if os.path.exists(bot['Welcome']):
            # Figure out which persona is calling the shots.
            # ChangeNickAvatar(bot,member)
            responses=ReadFile(bot['Welcome']).strip().split('\n')
            response=random.choice(responses).replace('{username}',f'**{member.mention}**')
            # Get the system welcome channel and send message there.
            syschannel=member.guild.system_channel
            await syschannel.send(response)
    except Exception as err:
        ErrorLog(f'OMJ: Error sending message: {sys.exc_info()[-1].tb_lineno}/{err}')

# Record the user leaving the server in the designated moderator area.

@client.event
async def on_member_remove(member):
    ErrorLog(f"OMR: {member}")

# Starts the bot

if __name__ == '__main__':
    # Retrieve tokens from environment variables
    TOKEN = os.getenv('DISCORD_TOKEN')

    # Check if bot token is provided
    if not TOKEN:
        print("The Discord token must be configured in the .env file.")
        sys.exit(1)

    # starts the bot with the corresponding token
    try:
        client.run(TOKEN, log_handler=None)
    except Exception as err:
        ErrorLog(f"Broken MAIN: {err}")
