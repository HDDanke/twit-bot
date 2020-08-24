import discord
from discord.ext import commands
import sqlite3, re, contextlib

class TweetDB(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect("twit.db")
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS Messages (
                message_id INTEGER PRIMARY KEY,
                channel_id INTEGER NOT NULL
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
        self.conn_sett = sqlite3.connect("settings.db")
        self.conn_sett.row_factory = sqlite3.Row
        self.conn_sett.execute("""
            CREATE TABLE IF NOT EXISTS Settings (
                channel_id INTEGER PRIMARY KEY,
                check_new INTEGER,
                insert_new INTEGER,
                read_history INTEGER
                );
            """)

    def __unload(self):
        self.conn.close()
        self.conn_sett.close()
        print("cogs.tweet: closed all database connections")

    def tweet_extract_ids(self, text):
        return re.findall('http[s]?://(?:mobile.)?twitter.com/((?:[a-zA-Z]|[0-9]|[_])+)/status/([0-9]+)', text)

    def insert_message(self, message_id, channel_id):
        try:
            self.conn.execute("INSERT INTO Messages(message_id, channel_id) VALUES(?,?)", (message_id, channel_id))
        except sqlite3.IntegrityError:
            return

    def insert_post(self, message_id, status_id):
        try:
            self.conn.execute("INSERT INTO Posts(message_id, status_id) VALUES(?,?)", (message_id, status_id))
        except sqlite3.IntegrityError:
            return

    def insert_tweet(self, artist_id, status_id):
        try:
            self.conn.execute("INSERT INTO Tweets(artist_id, status_id) VALUES(?,?)", (artist_id, status_id))
        except sqlite3.IntegrityError:
            return

    def is_status_in_db(self, status_id):
        with contextlib.closing(self.conn.cursor()) as cursor:
            cursor.execute("SELECT 1 FROM Tweets WHERE status_id = ? LIMIT 1", (status_id,))
            return cursor.fetchone()

    def is_message_in_db(self, message_id):
        with contextlib.closing(self.conn.cursor()) as cursor:
            cursor.execute("SELECT 1 FROM Messages WHERE message_id = ? LIMIT 1", (message_id,))
            return cursor.fetchone()

    def status_ids_from_message(self, message_id):
        with contextlib.closing(self.conn.cursor()) as cursor:
            cursor.execute("SELECT status_id FROM Posts WHERE message_id = ?", (message_id,))
            return cursor.fetchall()

    def delete_message(self, message_id):
        self.conn.execute("DELETE FROM Messages WHERE message_id = ?", (message_id,))

    def try_delete_tweet(self, status_id):
        try:
            self.conn.execute("DELETE FROM Tweets WHERE status_id = ?", (status_id,))
        except sqlite3.IntegrityError:
            return

    def get_last_messages_per_channel(self):
        with contextlib.closing(self.conn.cursor()) as cursor:
            cursor.execute("SELECT channel_id, MAX(message_id) FROM Messages GROUP BY channel_id ORDER BY message_id")
            return cursor.fetchall()

    def perm_on_message(self, channel_id):
        with contextlib.closing(self.conn_sett.cursor()) as cursor:
            cursor.execute("SELECT check_new, insert_new FROM Settings WHERE channel_id = ? LIMIT 1", (channel_id,))
            result = cursor.fetchone()
            if result:
                return result["check_new"], result["insert_new"]
            else:
                return 0, 0

    def perm_has_history(self, channel_id):
        with contextlib.closing(self.conn_sett.cursor()) as cursor:
            cursor.execute("SELECT read_history FROM Settings WHERE channel_id = ? LIMIT 1", (channel_id,))
            result = cursor.fetchone()
            if result:
                return result["read_history"]
            else:
                return 1

    @commands.Cog.listener()
    async def on_message(self, message):
        # ignore commands and bot messages
        if message.content.startswith('-') or message.author.bot:
            return

        # get channel permissions
        can_check_new, can_insert_new = self.perm_on_message(message.channel.id)
        # ignore message if channel has neither insert or check permissions
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
            self.insert_message(message.id, message.channel.id)

        for artist_id, status_id in arstats:
        # iterate through artist and status ids from message
            # check if status id is already in db
            if can_check_new and self.is_status_in_db(status_id):
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
        print(message.message_id)
        
        # check if message in db
        if self.is_message_in_db(message.message_id):
            print("removing from db")
            # get list of status ids from the soon to be deleted message
            tweets = [item[0] for item in self.status_ids_from_message(message.message_id)]
            # delete message and all posts referenced from it
            self.delete_message(message.message_id)
            # iterate through status ids and try to delete all unreferenced parents
            for status_id in tweets:
                self.try_delete_tweet(status_id)

    @commands.Cog.listener()
    async def on_ready(self):
        last_messages = self.get_last_messages_per_channel()
        print(last_messages)
        for channel_id, message_id in last_messages:
            print(f"channel_id: {channel_id} (type: {type(channel_id)})")
            print(f"message_id: {message_id} (type: {type(message_id)})")
            if self.perm_has_history(channel_id):
                channel = self.bot.get_channel(channel_id)
                async for message in channel.history(limit = None, after = message_id, oldest_first = True):
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
                            self.insert_message(message.id, message.channel.id)
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
        """channel = self.bot.get_channel(added_reaction.channel_id)
        message = await channel.fetch_message(added_reaction.message_id)
        for reaction in message.reactions:
            if reaction.me and reaction.emoji == '❌':
                await message.delete()
                break
        
        """
        # message = reaction.message
        #user == reaction.message.author and str(reaction.emoji) == '
    
    
    @commands.group(aliases = ["tdb"])
    async def tweetdb(self, ctx):
        pass

    @tweetdb.group(name ="table", aliases = ["tab"])
    @commands.is_owner()
    async def tdb_table(self, ctx):
        pass

    @tdb_table.group(name = "clear")
    async def tdb_tab_clear(self, ctx):
        pass
    
    @tdb_tab_clear.command(name = "all")
    async def tdb_tab_clear_all(self, ctx):
        self.conn.executescript("DELETE FROM Messages; DELETE FROM Tweets;")
        self.conn.commit()
        print("cogs.tweet: cleared all entries in twit.db")
    
    @tdb_tab_clear.command(name = "channel")
    @commands.guild_only()
    async def tdb_tab_clear_chanl(self, ctx, channel_id):
        print(channel_id)
        self.conn.execute("DELETE FROM Messages WHERE channel_id = ?", (channel_id,))
        self.conn.execute("DELETE FROM Tweets")
        self.conn.commit()
    
    @tdb_table.command(name = "insert")
    async def tdb_tab_insert(self, ctx, *channel_ids):
        for channel_id in channel_ids:
            print(channel_id)
            channel = self.bot.get_channel(int(channel_id))
            print(channel)
            async for message in channel.history(limit = None, oldest_first = True):
                # ignore bot commands
                if message.author.bot:
                        pass
                else:
                    # get all twitter artist ids and status ids from message
                    arstats = self.tweet_extract_ids(message.content)

                    # ignore message if no ids are found
                    if arstats != []:
                        self.insert_message(message.id, message.channel.id)
                        for artist_id, status_id in arstats:
                            self.insert_post(message.id, status_id)
                            self.insert_tweet(artist_id, status_id)
        self.conn.commit()
            
def setup(bot):
    bot.add_cog(TweetDB(bot))






