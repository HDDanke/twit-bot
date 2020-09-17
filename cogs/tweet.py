import discord
from discord.ext import commands
import sqlite3, re, contextlib

class TweetDB(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect("databases/twit.db")
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS Messages (
                message_id INTEGER PRIMARY KEY,
                channel_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL
                );

            CREATE TABLE IF NOT EXISTS Posts (
                post_id INTEGER PRIMARY KEY,
                status_id INTEGER REFERENCES Tweets(status_id),
                message_id INTEGER REFERENCES Messages(message_id) ON DELETE CASCADE,
                UNIQUE(status_id, message_id)
                );

            CREATE TABLE IF NOT EXISTS Tweets (
                status_id INTEGER PRIMARY KEY,
                artist_id TEXT NOT NULL
                );
            """)
        self.conn_sett = sqlite3.connect("databases/channel_settings.db")
        self.conn_sett.row_factory = sqlite3.Row

    def __unload(self):
        self.conn.close()
        self.conn_sett.close()
        print("cogs.tweet: closed all database connections")

    def tweet_extract_ids(self, text):
        return re.findall('http[s]?://(?:mobile.)?twitter.com/((?:[a-zA-Z]|[0-9]|[_])+)/status/([0-9]+)', text)

    def insert_message(self, message_id, channel_id, guild_id):
        try:
            self.conn.execute("INSERT INTO Messages(message_id, channel_id, guild_id) VALUES(?,?,?)", (message_id, channel_id, guild_id))
            return 0
        except sqlite3.IntegrityError:
            return 1

    def insert_post(self, message_id, status_id):
        try:
            self.conn.execute("INSERT INTO Posts(message_id, status_id) VALUES(?,?)", (message_id, status_id))
            return 0
        except sqlite3.IntegrityError:
            return 1

    def insert_tweet(self, artist_id, status_id):
        try:
            self.conn.execute("INSERT INTO Tweets(artist_id, status_id) VALUES(?,?)", (artist_id, status_id))
            return 0
        except sqlite3.IntegrityError:
            return 1

    def channel_perms(self, channel_id, guild_id):
        with contextlib.closing(self.conn_sett.cursor()) as cursor:
            cursor.execute("SELECT * FROM Settings WHERE channel_id = ? AND guild_id = ? LIMIT 1", (channel_id, guild_id))
            return cursor.fetchone()

    @commands.Cog.listener()
    async def on_message(self, message):
        
        def is_status_in_db(status_id):
            with contextlib.closing(self.conn.cursor()) as cursor:
                cursor.execute("SELECT 1 FROM Tweets WHERE status_id = ? LIMIT 1", (status_id,))
                return cursor.fetchone()
            
        # ignore commands and bot messages
        if message.content.startswith('-') or message.author.bot:
            return

        # get channel permissions
        perms = self.channel_perms(message.channel.id, message.guild.id)
        if perms == []:
                return
        can_check_new = perms["check_new_tweets"]
        can_insert_new = perms["insert_new_tweets"]
        # ignore message if channel has neither insert nor check permissions
        if not (can_check_new or can_insert_new):
            return

        # get all twitter artist ids and status ids from message
        arstats = self.tweet_extract_ids(message.content)
        print(f"cogs.tweet: found { len(arstats) } twitter links inside message")
        # ignore message if no ids are found
        if arstats == []:
            return
        
        # insert message into db
        if can_insert_new:
            self.insert_message(message.id, message.channel.id, message.guild.id)
        
        # iterate through artist and status ids from message        
        for artist_id, status_id in arstats:
            # check if status id is already in db
            if can_check_new and is_status_in_db(status_id):
                # rollback all inserts, break the loop and highlight the message
                if can_insert_new:
                    self.conn.rollback()
                await message.add_reaction('❌')
                break
            # else continue inserting
            elif can_insert_new:
                self.insert_post(message.id, status_id)
                self.insert_tweet(artist_id, status_id)
        else:
            if can_insert_new:
                self.conn.commit()

    @commands.Cog.listener()
    async def on_raw_message_delete(self, message):
        
        def is_message_in_db(message_id):
            with contextlib.closing(self.conn.cursor()) as cursor:
                cursor.execute("SELECT 1 FROM Messages WHERE message_id = ? LIMIT 1", (message_id,))
                return cursor.fetchone()
            
        def status_ids_from_message(message_id):
            with contextlib.closing(self.conn.cursor()) as cursor:
                cursor.execute("SELECT status_id FROM Posts WHERE message_id = ?", (message_id,))
                return cursor.fetchall()
                
        # check if message in db
        if is_message_in_db(message.message_id):
            # get list of status ids from the soon to be deleted message
            tweets = [item[0] for item in status_ids_from_message(message.message_id)]
            # delete message and all posts referenced from it
            self.conn.execute("DELETE FROM Messages WHERE message_id = ?", (message_id,))
            # iterate through status ids and try to delete all unreferenced parents
            for status_id in tweets:
                try:
                    self.conn.execute("DELETE FROM Tweets WHERE status_id = ? LIMIT 1", (status_id,))
                except sqlite3.IntegrityError:
                    return
            self.conn.commit()
 
    @commands.Cog.listener()
    async def on_ready(self):
    
        with contextlib.closing(self.conn.cursor()) as cursor:
            cursor.execute("SELECT guild_id, channel_id, MAX(message_id) FROM Messages GROUP BY channel_id ORDER BY message_id")
            last_messages = cursor.fetchall()
                
        print(last_messages)
        for guild_id, channel_id, message_id in last_messages:
            print(f"channel_id: {channel_id} (type: {type(channel_id)})")
            print(f"message_id: {message_id} (type: {type(message_id)})")
            perms = self.channel_perms(channel_id, guild_id)
            if perms == []:
                continue
            has_history = perms["insert_tweets_from_history"]  
            if has_history:
                channel = self.bot.get_channel(channel_id)
                msg_obj = discord.Object(message_id)
                async for message in channel.history(limit = None, after = msg_obj, oldest_first = True):
                    # ignore bot commands
                    if message.author.bot:
                            pass
                    else:
                        # get all twitter artist ids and status ids from message
                        arstats = self.tweet_extract_ids(message.content)

                        # ignore message if no ids are found
                        if arstats == []:
                            pass
                        else:
                            self.insert_message(message.id, message.channel.id, message.guild.id)
                            for artist_id, status_id in arstats:
                                self.insert_post(message.id, status_id)
                                self.insert_tweet(artist_id, status_id)
            self.conn.commit()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, reaction):
        if reaction.member.bot:
            return
        if reaction.emoji.name == '❌':
            channel = self.bot.get_channel(reaction.channel_id)
            message = await channel.fetch_message(reaction.message_id)
            await message.delete()
        # add author check
    
    
    @commands.group(name ="table", aliases = ["tab"])
    @commands.is_owner()
    async def table(self, ctx):
        pass

    @table.group(name = "clear")
    async def tab_clear(self, ctx):
        pass
    
    @tab_clear.command(name = "all")
    async def tab_clear_all(self, ctx):
        self.conn.executescript("DELETE FROM Messages; DELETE FROM Tweets; DELETE FROM Posts")
        self.conn.commit()
        print("cogs.tweet: cleared all entries in twit.db")
    
    @tab_clear.command(name = "channel")
    @commands.guild_only()
    async def tab_clear_chanl(self, ctx, channel_id):
        print(channel_id)
        self.conn.execute("DELETE FROM Messages WHERE channel_id = ?", (channel_id,))
        self.conn.execute("DELETE FROM Tweets")
        self.conn.commit()
    
    @table.command(name = "insert")
    async def tab_insert(self, ctx, *channel_ids):
        for channel_id in channel_ids:
            print(channel_id)
            channel = self.bot.get_channel(int(channel_id))
            print(channel)
            async for message in channel.history(limit = None, oldest_first = True):
                entries_count += 1
                # ignore bot commands
                if message.author.bot:
                        pass
                else:
                    # get all twitter artist ids and status ids from message
                    arstats = self.tweet_extract_ids(message.content)

                    # ignore message if no ids are found
                    if arstats != []:
                        tweets_count += 1
                        ins_msg_fail += self.insert_message(message.id, message.channel.id, message.guild.id)
                        for artist_id, status_id in arstats:
                            ins_pos_fail += self.insert_post(message.id, status_id)
                            ins_twt_fail += self.insert_tweet(artist_id, status_id)
            await ctx.send(f"{channel.name} done")
        await ctx.send(f"Found {tweets_count} tweets out of {entries_count} messages \nFailed inserts: \n{ins_msg_fail} in Messages \n{ins_pos_fail} in Posts \n{ins_twt_fail} in Tweets")         
        self.conn.commit()
                
def setup(bot):
    bot.add_cog(TweetDB(bot))






