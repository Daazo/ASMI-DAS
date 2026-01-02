import psutil
import time
import discord
from discord.ext import tasks
from datetime import datetime
import os
from brand_config import BrandColors, VisualElements, BOT_FOOTER

# Configuration
STATS_CHANNEL_ID = 1456612165774606398
UPDATE_INTERVAL = 60  # seconds

class LiveStats:
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()
        self.stats_message = None
        self.update_loop.start()

    def get_uptime(self):
        delta = int(time.time() - self.bot.start_time if hasattr(self.bot, 'start_time') else time.time() - self.start_time)
        days, remainder = divmod(delta, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{days}d {hours}h {minutes}m {seconds}s"

    @tasks.loop(seconds=UPDATE_INTERVAL)
    async def update_loop(self):
        if not self.bot.is_ready():
            return

        try:
            channel = self.bot.get_channel(STATS_CHANNEL_ID)
            if not channel:
                return

            # System metrics
            cpu_usage = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            mem_used = memory.used / (1024 * 1024)
            mem_total = memory.total / (1024 * 1024)
            
            # Bot metrics
            server_count = len(self.bot.guilds)
            user_count = sum(g.member_count for g in self.bot.guilds)
            
            # Count users in voice channels
            voice_users = 0
            for guild in self.bot.guilds:
                for vc in guild.voice_channels:
                    voice_users += len(vc.members)

            ping = round(self.bot.latency * 1000)

            embed = discord.Embed(
                title="💠 **RXT ENGINE Live Stats**",
                description=f"**System Statistics**\nReal-time updates of RXT ENGINE's status.\n\n{VisualElements.CIRCUIT_LINE}",
                color=BrandColors.PRIMARY,
                timestamp=datetime.now()
            )

            stats_info = (
                f"🌍 **Servers:** {server_count}\n"
                f"👤 **Users:** {user_count}\n"
                f"🎙️ **Voice:** {voice_users}\n\n"
                f"⏱️ **Uptime:** {self.get_uptime()}\n"
                f"📡 **Ping:** {ping}ms\n"
                f"💻 **CPU:** {cpu_usage}%\n"
                f"💾 **RAM:** {mem_used:.1f} / {mem_total:.1f} MB\n\n"
                f"♻️ **Refreshes:** in {UPDATE_INTERVAL} seconds"
            )

            embed.add_field(name="📊 **Metrics**", value=stats_info, inline=False)
            embed.set_footer(text=f"Auto-updates every {UPDATE_INTERVAL}s | {BOT_FOOTER}")
            
            # Set bot thumbnail
            if self.bot.user.avatar:
                embed.set_thumbnail(url=self.bot.user.avatar.url)

            if self.stats_message:
                try:
                    await self.stats_message.edit(embed=embed)
                except discord.NotFound:
                    self.stats_message = await channel.send(embed=embed)
            else:
                # Try to find existing message in history to avoid spam
                async for message in channel.history(limit=10):
                    if message.author == self.bot.user and message.embeds and "Live Stats" in message.embeds[0].title:
                        self.stats_message = message
                        await self.stats_message.edit(embed=embed)
                        break
                
                if not self.stats_message:
                    self.stats_message = await channel.send(embed=embed)

        except Exception as e:
            print(f"❌ [LIVE STATS ERROR] {e}")

def setup_live_stats(bot):
    return LiveStats(bot)
