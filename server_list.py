
import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime
from main import bot, log_action
import os

# Get support server channel ID from environment or use default
SUPPORT_SERVER_CHANNEL_ID = int(os.getenv('SERVER_LIST_CHANNEL_ID', '1406243267632300052'))

# Store the last sent message so it can be deleted
last_servers_message = None

@tasks.loop(minutes=10)
async def update_server_list():
    """Update the active server list every 10 minutes"""
    global last_servers_message

    try:
        channel = bot.get_channel(SUPPORT_SERVER_CHANNEL_ID)
        if channel is None:
            print(f"Server list channel {SUPPORT_SERVER_CHANNEL_ID} not found.")
            return

        # Build the embed content
        server_count = len(bot.guilds)
        
        embed = discord.Embed(
            title=f"🌴 **VAAZHA Bot - Active Servers** 🤖",
            description=f"**Currently serving {server_count} servers with ❤️**\n\n*Updated every 10 minutes automatically*",
            color=0x43b581,
            timestamp=datetime.utcnow()
        )
        
        # Sort servers by member count (largest first)
        sorted_guilds = sorted(bot.guilds, key=lambda g: g.member_count, reverse=True)
        
        # Add server information
        for i, guild in enumerate(sorted_guilds, 1):
            join_date = guild.me.joined_at.strftime("%Y-%m-%d") if guild.me.joined_at else "Unknown"
            owner_name = guild.owner.display_name if guild.owner else "Unknown"
            
            # Limit server name length for better display
            server_name = guild.name[:30] + "..." if len(guild.name) > 30 else guild.name
            
            embed.add_field(
                name=f"#{i} 🌐 {server_name}",
                value=f"👥 **Members:** {guild.member_count}\n🗓️ **Joined:** `{join_date}`\n👑 **Owner:** {owner_name}",
                inline=True
            )
            
            # Discord embed field limit is 25, so break if we reach that
            if i >= 24:  # Leave room for footer info
                break
        
        # If there are more servers than can be displayed
        if server_count > 24:
            embed.add_field(
                name="📊 **And More...**",
                value=f"+ {server_count - 24} additional servers",
                inline=False
            )
        
        embed.set_footer(
            text=f"🌴 VAAZHA Bot Status • Uptime: Running • Made with ❤️ by Daazo",
            icon_url=bot.user.display_avatar.url
        )
        embed.set_thumbnail(url=bot.user.display_avatar.url)

        # Delete previous message if exists
        try:
            if last_servers_message is not None:
                await last_servers_message.delete()
        except discord.NotFound:
            pass  # Message was already deleted
        except Exception as e:
            print(f"Error deleting previous server list message: {e}")

        # Send the new embed and save the message object
        last_servers_message = await channel.send(embed=embed)
        print(f"✅ Server list updated successfully ({server_count} servers)")

    except Exception as e:
        print(f"❌ Error updating server list: {e}")

@bot.event
async def on_guild_join_server_list_update(guild):
    """Update server list immediately when bot joins a new server"""
    print(f"📋 Bot joined new server: {guild.name} - Updating server list...")
    if update_server_list.is_running():
        update_server_list.restart()

@bot.event
async def on_guild_remove_server_list_update(guild):
    """Update server list immediately when bot leaves a server"""
    print(f"📋 Bot left server: {guild.name} - Updating server list...")
    if update_server_list.is_running():
        update_server_list.restart()

def start_server_list_monitoring():
    """Start the server list monitoring task"""
    if not update_server_list.is_running():
        update_server_list.start()
        print("✅ Server list monitoring started")

def stop_server_list_monitoring():
    """Stop the server list monitoring task"""
    if update_server_list.is_running():
        update_server_list.stop()
        print("⏹️ Server list monitoring stopped")

# Manual command to force update server list (owner only)
@bot.tree.command(name="update_server_list", description="🔧 Force update the active server list (Owner only)")
async def manual_update_server_list(interaction: discord.Interaction):
    bot_owner_id = os.getenv('BOT_OWNER_ID')
    if str(interaction.user.id) != bot_owner_id:
        await interaction.response.send_message("❌ Only the bot owner can use this command!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        await update_server_list()
        await interaction.followup.send("✅ Server list updated successfully!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error updating server list: {str(e)}", ephemeral=True)
