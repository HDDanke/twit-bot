import discord
from discord.ext import commands

class CogCommands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
    
    
    @commands.group(name = "cogs", hidden = True)
    @commands.is_owner()
    async def cogs(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Missing subcommand")
        
    
    @cogs.command(name = "load", hidden = True)
    @commands.is_owner()
    async def load_cog(self, ctx, *, cog: str):
        self.bot.load_extension('cogs.' + cog)
        await ctx.message.add_reaction('✅')
    
    @load_cog.error
    async def load_cog_e(self, ctx, error):
        await ctx.send(f"Error loading {cog}: {error}")
     
    
    @cogs.command(name = "unload", hidden = True)
    async def unload_cog(self, ctx, *, cog: str):
        self.bot.unload_extension('cogs.' + cog)
        await ctx.message.add_reaction('✅')
    
    @unload_cog.error
    async def unload_cog_e(self, ctx, error):
        await ctx.send(f"Error unloading {cog}: {error}")
        
    
    @cogs.command(name = "reload", hidden = True)
    async def reload_cog(self, ctx, *, cog: str):
        self.bot.reload_extension('cogs.' + cog)
        await ctx.message.add_reaction('✅')
    
    @reload_cog.error
    async def reload_cog_e(self, ctx, error):
        await ctx.send(f"Error reloading {cog}: {error}")


def setup(bot):
    bot.add_cog(CogCommands(bot))
