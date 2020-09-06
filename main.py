import discord
from discord.ext import commands

with open("token.txt","r") as file:
    TOKEN = file.readline()

bot = commands.Bot('-')

extensions = ['cogs.tweet', 'cogs.cogs', 'cogs.settings']

if __name__ == '__main__':
    for extension in extensions:
        bot.load_extension(extension)

@bot.event
async def on_ready():

    print(f'\n\nLogged in as: {bot.user.name} - {bot.user.id}\nVersion: {discord.__version__}\n')
    game = discord.Game("with links (v3)")
    await bot.change_presence(activity=game)

@bot.command(hidden=True)
@commands.is_owner()
async def stop(ctx):
    await ctx.bot.logout()

bot.run(TOKEN, bot=True, reconnect=True)