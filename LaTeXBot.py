
# LaTeXBot.py -- a simple LaTeX parser for Discord
#   Nilay Kumar, 15 Aug 2018
#
# dependencies: python3, ghostscript, latex (with standalone)
#
# LaTeXBot.py activates upon detecting Discord messages starting with a
# customizable PREFIX upon which the rest of the message is treated
# LaTeX code and compiled as an (inline) equation in a customizable
# template. The default template uses pdflatex and the 'standalone'
# package. The resulting pdf file is then converted to a png using
# ghostscript and sent back to the Discord channel.

import discord
import subprocess
import datetime

# the prefix used to invoke the compiler
# e.g. 'PREFIX \int_M C_*(-) \simeq C_*(M)'
PREFIX = '$$'

# the prefix used to run bot commands
PREFIX_COMMAND = '!'

# DPI of the output png
DPI = 500

# folder in which the TeX templates are installed
TEMPLATE_DIR = 'templates/'

# folder in which the user macros are installed
MACRO_DIR = 'macros/'

# folder in which pdflatex and ghostscript are run
TMP_DIR = 'tmp/'

client = discord.Client()

# upon receiving a message from anyone in the channel...
@client.event
async def on_message(message):

    # ignore messages from myself
    # not an issue unless the bot sends messages with PREFIX
    if message.author == client.user:
        return

    # if the macros file for this user doesn't exist, create an empty one
    macroFileName = str(message.author).replace('#', '')
    subprocess.run(['touch %s%s.tex' % (MACRO_DIR, macroFileName)], shell=True)

    # if the message is latex code
    if message.content.startswith(PREFIX):
        # clean up the directory containing the temporary files
        # this will need to be modified if the bot is made async
        subprocess.run(['rm %s* 2>/dev/null' % TMP_DIR], stdout=subprocess.DEVNULL, shell=True)
        # grab the relevant latex from the message
        latex = message.content[len(PREFIX):].strip()
        # if all we have is whitespace, do nothing
        if(len(latex)==0):
            return
        # keep track of the message id
        # our temporary files will be named based on these
        # message ids, which might be important if the bot is made async
        messageId = message.id
        # start my stopwatch
        t1 = datetime.datetime.now()
        # set the default TeX macros file (relative to tmp/, mind you)
        macros = '\input{../%s%s.tex}' % (MACRO_DIR, macroFileName)
        # create a TeX file based on the template, macros, and the given latex code
        with open('%stmp%s.tex' % (TMP_DIR, messageId), 'w+') as f:
            f.write(template % (macros, latex))
        # here's the real work
        # working in the temp directory, compile the TeX file into a pdf
        # then convert it to a png
        completedProcess = subprocess.run(['cd %s; pdflatex -halt-on-error tmp%s.tex; gs -sDEVICE=pngalpha -dTextAlphaBits=4 -dGraphicsAlphaBits=4 -r%d -o tmp%s.png tmp%s.pdf' % (TMP_DIR, messageId, DPI, messageId, messageId)], stdout=subprocess.PIPE, shell=True)
        # stop my stopwatch
        t2 = datetime.datetime.now()

        if completedProcess.returncode == 0:
            # everything went ok
            print('SUCCESS --> Parsed [%s] from %s in %d ms' % (latex, message.author, (t2-t1).total_seconds()*1000))
            # send the final png file to Discord
            await client.send_file(message.channel, '%stmp%s.png' % (TMP_DIR, messageId))
            return
        else:
            # something went wrong!
            # it's probably the TeX compiler whining
            # find a line starting with '!'. that's probably the error.
            rawOutput = completedProcess.stdout.decode('utf-8')
            # uncomment the next line to output the full output
            #print(rawOutput)
            texError = ((rawOutput.split('\n!'))[1].split('\n')[0].strip())
            print('FAILURE --> Error parsing [%s] from %s : %s ' % (latex, message.author, texError))
            # notify Discord of the error
            await client.send_message(message.channel, 'LaTeXBot ERROR >> %s' % texError)
            return

    # if the message wants to run a bot command...
    if message.content.startswith(PREFIX_COMMAND):
        # grab the relevant command
        command = message.content[len(PREFIX_COMMAND):].strip()

        print('%s told me to [%s].' % (message.author, command))

        # parse macro-related commands
        if command.startswith('help'):
            # !help displays a brief description of these commands
            await client.send_message(message.channel, 'The help feature is currently under construction.')
            return
        elif command.startswith('macros'):
            # !macros manipulate the user's macros
            macroCommand = command[6:].strip()
            if(macroCommand == 'ls'):
                # !macros ls displays the user's stored macros
                # read the appropriate macros file
                with open('%s%s.tex' % (MACRO_DIR, macroFileName), 'r') as f:
                    macrosls = f.read().rstrip()
                    if len(macrosls) == 0:
                        # if the macros file is empty, notify the user
                        await client.send_message(message.channel, '%s seems to have no macros set...' % message.author)
                        return
                    else:
                        # otherwise, display the macros in a code block
                        macroslsnumbered = '%s\'s macros:\n```\n' % message.author
                        # display the macros with line numbers
                        for index, s in enumerate(macrosls.split('\n')):
                            macroslsnumbered += ('%d\t%s\n' % (index, s))
                        macroslsnumbered += '```'
                        # send the numbered list of macros
                        await client.send_message(message.channel, macroslsnumbered)
                        return
            elif(macroCommand[0:3] == 'add'):
                # !macros add blah appends 'blah' as a new line in the relevant macros file
                # grab the macro to be added
                macroToAdd = macroCommand[3:].strip()
                if len(macroToAdd) == 0:
                    await client.send_message(message.channel, 'Not adding a macro...')
                    return
                # append said macro to the macros file
                with open('%s%s.tex' % (MACRO_DIR, macroFileName), 'a+') as f:
                    f.write('%s\n' % macroToAdd)
                # notify the user
                await client.send_message(message.channel, 'Added macro `%s`.' % macroToAdd)
                return
            elif(macroCommand[0:2] == 'rm'):
                # !macros rm i removes the ith macro (zero-indexed)
                try:
                    lineNumber = int(macroCommand[2:].strip())
                    with open('%s%s.tex' % (MACRO_DIR, macroFileName), 'r+') as f:
                        total = f.readlines()
                        # abort if there are fewer macros than the requested lineNumber
                        if (len(total) - 1 < lineNumber or lineNumber < 0):
                            await client.send_message(message.channel, 'Could not find macro number %d!' % lineNumber)
                            return
                        f.seek(0)
                        for index, s in enumerate(total):
                            if index != lineNumber:
                                f.write(s)
                        f.truncate()
                        await client.send_message(message.channel, 'Removed macro [%s].' % total[lineNumber].rstrip())
                    return
                except ValueError:
                    # notify the user that they are using rm incorrectly
                    if(macroCommand[2:].strip() == '*'):
                        subprocess.run(['rm %s%s.tex' % (MACRO_DIR, macroFileName)], shell=True)
                        await client.send_message(message.channel, 'Removed all of %s\'s macros.' % message.author)
                        return
                    await client.send_message(message.channel, 'Invalid macro number supplied!')
                    return
        else:
            await client.send_message(message.channel, 'Unknown command entered.')

@client.event
async def on_ready():
    print('LaTeXBot.py logged in as %s with id %s.\n----------' % (client.user.name, client.user.id))




# read the default TeX template
with open('%sdefault.tex' % TEMPLATE_DIR, 'r') as f:
    template = f.read()

# read the Discord OAuth2 token
with open('token', 'r') as f:
    token = f.readline().rstrip()

# in case the relevant directories do not exist, create them
# the template dir is expected to exist already, so we don't bother with that
subprocess.run(['mkdir -p %s' % MACRO_DIR], shell=True, stdout=subprocess.DEVNULL)
subprocess.run(['mkdir -p %s' % TMP_DIR], shell=True, stdout=subprocess.DEVNULL)

# connect to the Discord server
client.run(token)

