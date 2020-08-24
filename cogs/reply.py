from discord.ext.commands import Cog, command
from discord.utils import get
from discord.errors import InvalidArgument
from discord import Webhook, AsyncWebhookAdapter, Embed, File
from urllib.request import Request, urlopen
import aiohttp
import os
import re


class Reply(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.IMG_EXT = [".jpg", ".png", ".jpeg", ".gif", ".gifv"]
        self.VIDEO_EXT = [".mp4", ".avi", ".flv", ".mov", ".wmv"]
        self.match_message = re.compile(r"^((> ([^\n]*)\n)+)((<@![0-9]{18}>)|(@[^#]+#0000)) ([\s\S]*)$")
        self.strip_quote = re.compile(r"\n> ([^\n]*)")

    @Cog.listener()
    async def on_message(self, msg):
        """
        When a message is sent check if that message is actually a reply
        to another message and if so delete it and turn it into a webhooked reply
        """
        if msg.author.bot:
            return

        reply_msg = None
        search = self.match_message.search(msg.content)
        if search:
            message = "\n".join([line[2:] for line in search.group(1).split("\n")])[:-1]
            if (search.group(5)):
                sender = int(search.group(5)[3:-1])
            else:
                sender = None
            content = search.group(7)

            async for old_msg in msg.channel.history(limit=10000):
                match_sender = (sender is None and old_msg.author.bot) or old_msg.author.id == sender
                match_content = old_msg.content == message or self.strip_quote.sub("", "\n" + old_msg.content) == "\n" + message
                if match_sender and match_content:
                    reply_msg = old_msg
                    msg.content = content
                    break

        if reply_msg:
            if msg.attachments:
                req = Request(url=msg.attachments[0].url, headers={'User-Agent': 'Mozilla/5.0'})
                webpage = urlopen(req).read()
                with open(msg.attachments[0].filename, 'wb') as f:
                    f.write(webpage)

        if reply_msg:
            webhook = await msg.channel.create_webhook(name="Placeholder")
            await self.send_message(msg.author, await self.create_embed(reply_msg.author, reply_msg), msg, webhook)
            await webhook.delete()
            await msg.delete()

    async def create_embed(self, author, author_message):
        """
        Create the embed with the contents of the message that is being
        replied to
        :param author: Author (User object) of the message
        :param author_message: The contents of the message
        :return: Embed object with the message contents and user info along with
        hyperlink to the message being replied to
        """
        embed = Embed(colour=author.color)

        if author_message.clean_content:
            embed.add_field(name=author.display_name, value=f"{author_message.clean_content}\n[[jump]]({author_message.jump_url})")

        if author_message.attachments:
            for att in author_message.attachments:
                for ext in self.IMG_EXT:
                    if ext in att.filename:
                        break
                else:
                    for ext in self.VIDEO_EXT:
                        if ext in att.filename:
                            embed.add_field(name="\u200b", value=f"🎞️ {att.filename}", inline=False)
                            break
                    else:
                        embed.add_field(name="\u200b", value=f"📁 {att.filename}", inline=False)
                        break
                    break
                embed.set_image(url=f"{att.url}")

        if author_message.embeds and not author_message.attachments:
            for embed in author_message.embeds:
                embed.clear_fields()
                embed.set_image(url="")
                embed.add_field(name=author.display_name, value=author_message.clean_content)

        embed.set_thumbnail(url=author.avatar_url_as(size=32, format='png'))

        if not author_message.clean_content:
            embed.add_field(name="\u200b", value=f"[[jump]]({author_message.jump_url})", inline=False)

        return embed

    async def send_message(self, original_user, embed, message, webhook):
        """
        Sends a message impersonating the user that called the reply
        functionality
        :param original_user: User who send the reply message
        :param embed: Embed object that contains original_user info and message content
        :param message: Message of the reply that original_user sent
        :param webhook: Webhook that will get customized to impersonate original_user
        """
        avatar_url = original_user.avatar_url_as(size=128, format='png')
        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url(webhook.url, adapter=AsyncWebhookAdapter(session))

            if message.attachments:
                for att in message.attachments:
                    for ext in self.IMG_EXT:
                        if ext in att.filename:
                            with open(att.filename, 'rb') as f:
                                await webhook.send(embed=embed,
                                                   wait=True,
                                                   username=original_user.display_name,
                                                   avatar_url=avatar_url,
                                                   )
                                await webhook.send(content=message.content,
                                                   username=original_user.display_name,
                                                   avatar_url=avatar_url,
                                                   file=File(f)
                                                   )

                            os.remove(att.filename)
                            return
                    else:
                        for ext in self.VIDEO_EXT:
                            if ext in att.filename:
                                with open(att.filename, 'rb') as f:
                                    await webhook.send(embed=embed,
                                                       wait=True,
                                                       username=original_user.display_name,
                                                       avatar_url=avatar_url,
                                                       )
                                    await webhook.send(content=message.content,
                                                       username=original_user.display_name,
                                                       avatar_url=avatar_url,
                                                       file=File(f)
                                                       )
                                os.remove(att.filename)
                                return
                        else:
                            with open(att.filename, 'rb') as f:
                                await webhook.send(embed=embed,
                                                   wait=True,
                                                   username=original_user.display_name,
                                                   avatar_url=avatar_url,
                                                   )
                                await webhook.send(content=message.content,
                                                   username=original_user.display_name,
                                                   avatar_url=avatar_url,
                                                   file=File(f)
                                                   )
                            os.remove(att.filename)
                            return

            await webhook.send(embed=embed,
                               wait=True,
                               username=original_user.display_name,
                               avatar_url=avatar_url
                               )
            await webhook.send(content=message.content,
                               username=original_user.display_name,
                               avatar_url=avatar_url
                               )
