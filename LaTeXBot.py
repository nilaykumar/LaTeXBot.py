
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

# TODO implement per-user macros
# TODO implement templates
# TODO normalize output sizes
# TODO allow customization of parameters
# TODO add non-inline equation support

import discord
import subprocess
import datetime

# the prefix used to invoke the bot
# e.g. 'PREFIX \int_M C_*(-) \simeq C_*(M)'
PREFIX = '$$'

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

    # if the message starts with PREFIX...
    if message.content.startswith(PREFIX):
        # clean up the directory containing the temporary files
        # this will need to be modified if the bot is made async
        subprocess.run(['rm %s*' % TMP_DIR], stdout=subprocess.DEVNULL, shell=True)
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
        # create a TeX file based on the template and the given latex code
        with open('%stmp%s.tex' % (TMP_DIR, messageId), 'w+') as f:
            f.write(template % latex)
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
        else:
            # something went wrong!
            # it's probably the TeX compiler whining
            # find a line starting with '!'. that's probably the error.
            texError=((completedProcess.stdout.decode('utf-8').split('\n!'))[1].split('\n')[0].strip())
            print('FAILURE --> Error parsing [%s] from %s : %s ' % (latex, message.author, texError))
            # notify Discord of the error
            await client.send_message(message.channel, 'LaTeXBot ERROR >> %s' % texError)

@client.event
async def on_ready():
    print('LaTeXBot.py logged in as %s with id %s.\n----------' % (client.user.name, client.user.id))




# read the default TeX template
with open('%sdefault.tex' % TEMPLATE_DIR, 'r') as f:
    template = f.read()

# read the Discord OAuth2 token
with open('token', 'r') as f:
    token = f.readline().rstrip()

# connect to the Discord server
client.run(token)

