from discord.ext import commands, tasks
from datetime import datetime
import discord


class Message(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return
        channel = self.bot.get_channel(882207091887046676)
        embed=discord.Embed(color=0x9d4d4d)
        embed.set_author(name=f"Deleted Message")
        embed.add_field(name="Message:", value=f"{message.content}")
        embed.add_field(name=f"Author", value=f"{message.author}, ({message.author.id})", inline=False)
        embed.add_field(name=f"Channel", value=f"{message.channel.name}, ({message.channel.id})", inline=False)
        embed.set_footer(text=datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        await channel.send(embed=embed)

def setup(bot):
    bot.add_cog(Message(bot))
