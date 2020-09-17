import discord
from discord.ext import commands

class CogCommands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
    
    
    @commands.group(name = "cogs", hidden = True)
    @commands.is_owner()
    async def cogs(self, ctx):
        pass
        
    @cogs.command(name = "load", hidden = True)
    async def load_cog(self, ctx, *, cog: str):

        try:
            self.bot.load_extension('cogs.' + cog)
        except Exception:
            await ctx.message.add_reaction('❌')
            await ctx.send(f"Error loading {cog}: {Exception}")
        else:
            await ctx.message.add_reaction('✅')

    @cogs.command(name = "unload", hidden = True)
    async def unload_cog(self, ctx, *, cog: str):

        try:
            self.bot.unload_extension('cogs.' + cog)
        except Exception:
            await ctx.message.add_reaction('❌')
            await ctx.send(f"Error unloading {cog}: {Exception}")
        else:
            await ctx.message.add_reaction('✅')

    @cogs.command(name = "reload", hidden = True)
    async def reload_cog(self, ctx, *, cog: str):
        try:
            self.bot.reload_extension('cogs.' + cog)
        except Exception:
            await ctx.message.add_reaction('❌')
            await ctx.send(f"Error reloading {cog}: {Exception}")
        else:
            await ctx.message.add_reaction('✅')


def setup(bot):
    bot.add_cog(CogCommands(bot))