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
        self.channel_id = STATS_CHANNEL_ID
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
            # Strictly try to get the channel
            channel = self.bot.get_channel(self.channel_id)
            
            if not channel:
                try:
                    channel = await self.bot.fetch_channel(self.channel_id)
                except:
                    pass
            
            if not channel:
                # If still not found, search by name in all guilds as a backup
                for guild in self.bot.guilds:
                    for ch in guild.text_channels:
                        if ch.name == "live-stats" or ch.id == self.channel_id:
                            channel = ch
                            self.channel_id = ch.id
                            break
                    if channel: break

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
            
            if self.bot.user.avatar:
                embed.set_thumbnail(url=self.bot.user.avatar.url)

            if self.stats_message:
                try:
                    await self.stats_message.edit(embed=embed)
                except:
                    self.stats_message = await channel.send(embed=embed)
            else:
                # Look for existing message
                async for message in channel.history(limit=5):
                    if message.author == self.bot.user and message.embeds and "Live Stats" in message.embeds[0].title:
                        self.stats_message = message
                        await self.stats_message.edit(embed=embed)
                        break
                
                if not self.stats_message:
                    self.stats_message = await channel.send(embed=embed)

        except Exception as e:
            print(f"❌ [LIVE STATS ERROR] {e}")

def setup_live_stats(bot):
    # Add a slash command to set the channel manually
    @bot.tree.command(name="setstats", description="Set the current channel for live statistics (Owner only)")
    async def setstats(interaction: discord.Interaction):
        bot_owner_id = os.getenv('BOT_OWNER_ID')
        if str(interaction.user.id) != bot_owner_id:
            await interaction.response.send_message("❌ Only the bot owner can use this command!", ephemeral=True)
            return
        
        bot.live_stats.channel_id = interaction.channel.id
        bot.live_stats.stats_message = None # Reset to send a new message
        await interaction.response.send_message(f"✅ Live stats will now be sent to {interaction.channel.mention}", ephemeral=True)
        await bot.live_stats.update_loop()

    return LiveStats(bot)
