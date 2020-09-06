import discord
from discord.ext import commands

class CogCommands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='load', hidden=True)
    @commands.is_owner()
    async def load_cog(self, ctx, *, cog: str):

        try:
            self.bot.load_extension(cog)
        except Exception:
            await ctx.message.add_reaction('❌')
            await ctx.send(f"Error loading {cog}: {Exception}")
        else:
            await ctx.message.add_reaction('✅')

    @commands.command(name='unload', hidden=True)
    @commands.is_owner()
    async def unload_cog(self, ctx, *, cog: str):

        try:
            self.bot.unload_extension(cog)
        except Exception:
            await ctx.message.add_reaction('❌')
            await ctx.send(f"Error unloading {cog}: {Exception}")
        else:
            await ctx.message.add_reaction('✅')

    @commands.command(name='reload', hidden=True)
    @commands.is_owner()
    async def reload_cog(self, ctx, *, cog: str):
        try:
            self.bot.reload_extension(cog)
        except Exception:
            await ctx.message.add_reaction('❌')
            await ctx.send(f"Error reloading {cog}: {Exception}")
        else:
            await ctx.message.add_reaction('✅')


def setup(bot):
    bot.add_cog(CogCommands(bot))