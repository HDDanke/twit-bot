import discord
from discord.ext import commands
import sqlite3

class Settings(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect("databases/channel_settings.db")
        self.conn.row_factory = sqlite3.Row
        self.ch_sett_dict = {
                "check_new_tweets": {
                    "sqtype": "INTEGER",
                    "pytype": "bool"
                    },
                "insert_new_tweets": {
                    "sqtype": "INTEGER",
                    "pytype": "bool"
                    },
                "insert_tweets_from_history": {
                    "sqtype": "INTEGER",
                    "pytype": "bool"
                    }
            }
                    
        self.conn.execute("CREATE TABLE IF NOT EXISTS Settings (channel_id INTEGER PRIMARY KEY, guild_id INTEGER, {});".format((', ').join(key + self.ch_sett_dict[key]['sqtype'] for key in self.ch_sett_dict)))
            
    def __unload(self):
        self.conn.close()
        print("cogs.settings: closed all database connections")
        
    @commands.group()
    @commands.is_owner()
    async def channel_settings (self, ctx, column: str, value: int, channel_id = None):
        if channel_id == None:
            channel_id = ctx.channel.id
        if column in ch_sett_dict:
            self.conn.execute(f"INSERT INTO Settings(channel_id,guild_id,{column}) VALUES(?,?,?) ON CONFLICT(channel_id) DO UPDATE SET {column}=excluded.{column}", (channel_id, ctx.guild.id, value))
            self.conn.commit()
        else:
            await ctx.send("Unknown channel setting")
def setup(bot):
    bot.add_cog(Settings(bot))
