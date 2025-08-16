
import discord
from discord.ext import commands
import asyncio
from datetime import datetime
import os
from main import bot, get_server_data

# ==== GLOBAL LOGGING CONFIGURATION ====
SUPPORT_SERVER_ID = int(os.getenv('SUPPORT_SERVER_ID', '1404842638615777331'))
LOG_CATEGORY_ID = int(os.getenv('LOG_CATEGORY_ID', '1405764734812160053'))

# Global logging channels cache
global_log_channels = {}

async def get_or_create_global_channel(channel_name: str):
    """Get or create a global logging channel in the support server"""
    if not SUPPORT_SERVER_ID or not LOG_CATEGORY_ID:
        return None
    
    # Check cache first
    if channel_name in global_log_channels:
        channel = bot.get_channel(global_log_channels[channel_name])
        if channel:
            return channel
    
    try:
        support_guild = bot.get_guild(SUPPORT_SERVER_ID)
        if not support_guild:
            return None
            
        category = discord.utils.get(support_guild.categories, id=LOG_CATEGORY_ID)
        if not category:
            return None

        # Try to find existing channel
        channel = discord.utils.get(category.text_channels, name=channel_name.lower())
        if channel:
            global_log_channels[channel_name] = channel.id
            return channel

        # Create new channel
        channel = await support_guild.create_text_channel(
            name=channel_name.lower(),
            category=category,
            topic=f"Global logs for {channel_name} - VAAZHA Bot"
        )
        global_log_channels[channel_name] = channel.id
        return channel
    except Exception as e:
        print(f"Error creating global log channel {channel_name}: {e}")
        return None

async def log_to_global(channel_name: str, embed: discord.Embed):
    """Send log message to global logging channel"""
    try:
        channel = await get_or_create_global_channel(channel_name)
        if channel:
            await channel.send(embed=embed)
    except Exception as e:
        print(f"Error logging to global channel {channel_name}: {e}")

async def setup_global_channels():
    """Setup all global logging channels"""
    if not SUPPORT_SERVER_ID or not LOG_CATEGORY_ID:
        print("⚠️ Global logging disabled - SUPPORT_SERVER_ID and LOG_CATEGORY_ID not configured")
        return
    
    # Global channels to create
    global_channels = [
        "dm-logs",
        "bot-dm-send-logs", 
        "live-console",
        "command-errors",
        "bot-events",
        "security-alerts"
    ]
    
    for channel_name in global_channels:
        await get_or_create_global_channel(channel_name)
    
    # Create per-server channels for existing guilds
    for guild in bot.guilds:
        if guild.id != SUPPORT_SERVER_ID:  # Don't create logs for support server itself
            # Clean server name for channel naming
            clean_name = guild.name.lower().replace(" ", "-").replace("_", "-")
            # Remove special characters and limit length
            clean_name = ''.join(c for c in clean_name if c.isalnum() or c == '-')[:45]
            channel_name = f"{clean_name}-logs"
            await get_or_create_global_channel(channel_name)
    
    print(f"✅ Global logging system initialized with {len(global_log_channels)} channels")

# Global logging functions
async def log_dm_received(message):
    """Log DMs received by bot"""
    embed = discord.Embed(
        title="📥 DM Received",
        description=f"**From:** {message.author} ({message.author.id})\n**Content:** {message.content[:1000]}",
        color=0x3498db,
        timestamp=datetime.now()
    )
    embed.set_footer(text=f"User ID: {message.author.id}")
    if message.author.display_avatar:
        embed.set_thumbnail(url=message.author.display_avatar.url)
    await log_to_global("dm-logs", embed)

async def log_dm_sent(recipient, content):
    """Log DMs sent by bot"""
    if not recipient:
        return  # Skip logging if recipient is None
        
    embed = discord.Embed(
        title="📤 DM Sent By Bot", 
        description=f"**To:** {recipient} ({recipient.id})\n**Content:** {content[:1000]}",
        color=0x43b581,
        timestamp=datetime.now()
    )
    embed.set_footer(text=f"Recipient ID: {recipient.id}")
    if recipient.display_avatar:
        embed.set_thumbnail(url=recipient.display_avatar.url)
    await log_to_global("bot-dm-send-logs", embed)

async def log_console_event(event_type: str, message: str):
    """Log console events like bot start/restart"""
    embed = discord.Embed(
        title=f"🖥️ Console Event: {event_type}",
        description=message,
        color=0x9b59b6,
        timestamp=datetime.now()
    )
    embed.set_footer(text="VAAZHA Bot Console")
    await log_to_global("live-console", embed)

async def log_command_error(interaction_or_ctx, error):
    """Log command errors globally"""
    if hasattr(interaction_or_ctx, 'guild'):
        guild = interaction_or_ctx.guild
        user = interaction_or_ctx.user if hasattr(interaction_or_ctx, 'user') else interaction_or_ctx.author
        command = getattr(interaction_or_ctx, 'command', 'Unknown')
    else:
        guild = None
        user = None
        command = 'Unknown'
    
    embed = discord.Embed(
        title="❌ Command Error",
        description=f"**Guild:** {guild.name if guild else 'DM'} ({guild.id if guild else 'N/A'})\n"
                   f"**User:** {user} ({user.id if user else 'N/A'})\n"
                   f"**Command:** {command}\n"
                   f"**Error:** {str(error)[:1000]}",
        color=0xe74c3c,
        timestamp=datetime.now()
    )
    embed.set_footer(text=f"Error Type: {type(error).__name__}")
    await log_to_global("command-errors", embed)

async def log_guild_join_global(guild):
    """Log when bot joins a server"""
    # Create guild-specific log channel with clean name
    clean_name = guild.name.lower().replace(" ", "-").replace("_", "-")
    clean_name = ''.join(c for c in clean_name if c.isalnum() or c == '-')[:45]
    channel_name = f"{clean_name}-logs"
    await get_or_create_global_channel(channel_name)
    
    # Log the join event
    embed = discord.Embed(
        title="🎉 Bot Joined New Server",
        description=f"**Server:** {guild.name}\n**ID:** {guild.id}\n**Owner:** {guild.owner}\n**Members:** {guild.member_count}\n**Log Channel:** {channel_name}",
        color=0x43b581,
        timestamp=datetime.now()
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    await log_to_global("bot-events", embed)

async def log_guild_remove_global(guild):
    """Log when bot leaves a server"""
    # Try to delete the server's log channel
    clean_name = guild.name.lower().replace(" ", "-").replace("_", "-")
    clean_name = ''.join(c for c in clean_name if c.isalnum() or c == '-')[:45]
    channel_name = f"{clean_name}-logs"
    
    try:
        support_guild = bot.get_guild(SUPPORT_SERVER_ID)
        if support_guild:
            category = discord.utils.get(support_guild.categories, id=LOG_CATEGORY_ID)
            if category:
                channel = discord.utils.get(category.text_channels, name=channel_name)
                if channel:
                    await channel.delete()
                    if channel_name in global_log_channels:
                        del global_log_channels[channel_name]
    except Exception as e:
        print(f"Error deleting log channel for {guild.name}: {e}")
    
    embed = discord.Embed(
        title="👋 Bot Left Server",
        description=f"**Server:** {guild.name}\n**ID:** {guild.id}\n**Members:** {guild.member_count}\n**Log Channel:** {channel_name} (deleted)",
        color=0xe74c3c,
        timestamp=datetime.now()
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    await log_to_global("bot-events", embed)

async def log_global_activity(activity_type: str, guild_id: int, user_id: int, details: str):
    """Log general bot activity to global channels"""
    guild = bot.get_guild(guild_id) if guild_id else None
    user = bot.get_user(user_id) if user_id else None
    
    embed = discord.Embed(
        title=f"🔍 {activity_type}",
        description=f"**Server:** {guild.name if guild else 'Unknown'} ({guild_id})\n"
                   f"**User:** {user if user else 'Unknown'} ({user_id})\n"
                   f"**Details:** {details}",
        color=0x9b59b6,
        timestamp=datetime.now()
    )
    
    # Log to server-specific channel
    if guild_id and guild_id != SUPPORT_SERVER_ID and guild:
        clean_name = guild.name.lower().replace(" ", "-").replace("_", "-")
        clean_name = ''.join(c for c in clean_name if c.isalnum() or c == '-')[:45]
        channel_name = f"{clean_name}-logs"
        await log_to_global(channel_name, embed)

async def log_bot_command_activity(guild_id: int, command_type: str, user, details: str):
    """Log specific bot command activities to per-server channel"""
    guild = bot.get_guild(guild_id)
    if not guild or guild.id == SUPPORT_SERVER_ID:
        return
    
    # Use clean server name for channel
    clean_name = guild.name.lower().replace(" ", "-").replace("_", "-")
    clean_name = ''.join(c for c in clean_name if c.isalnum() or c == '-')[:45]
    channel_name = f"{clean_name}-logs"
    
    # Set color based on command type
    colors = {
        'economy': 0xf1c40f,
        'karma': 0x9b59b6,
        'security': 0xe74c3c,
        'moderation': 0xe74c3c,
        'voice': 0x3498db,
        'general': 0x95a5a6,
        'communication': 0x43b581
    }
    
    embed = discord.Embed(
        title=f"🤖 Bot Command Activity - {command_type.title()}",
        description=f"**User:** {user}\n**Details:** {details}",
        color=colors.get(command_type.lower(), 0x3498db),
        timestamp=datetime.now()
    )
    embed.set_footer(text=f"Server: {guild.name} (ID: {guild.id})")
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    await log_to_global(channel_name, embed)

async def log_bot_content_shared(guild_id: int, command_used: str, user, content: str, channel_name: str = None):
    """Log content shared by bot through commands like /say, /announce, etc."""
    guild = bot.get_guild(guild_id)
    if not guild or guild.id == SUPPORT_SERVER_ID:
        return
    
    # Use clean server name for channel
    clean_name = guild.name.lower().replace(" ", "-").replace("_", "-")
    clean_name = ''.join(c for c in clean_name if c.isalnum() or c == '-')[:45]
    log_channel_name = f"{clean_name}-logs"
    
    embed = discord.Embed(
        title=f"📢 Bot Content Shared - {command_used.upper()}",
        description=f"**Command:** {command_used}\n**User:** {user}\n**Channel:** {channel_name if channel_name else 'Current channel'}\n**Content:** {content[:800]}{'...' if len(content) > 800 else ''}",
        color=0x43b581,
        timestamp=datetime.now()
    )
    embed.set_footer(text=f"Server: {guild.name} (ID: {guild.id})")
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    await log_to_global(log_channel_name, embed)

# Event handlers
async def global_on_message(message):
    """Global message handler for logging"""
    if message.author.bot:
        # Check if it's the bot sending a DM
        if message.author.id == bot.user.id and isinstance(message.channel, discord.DMChannel):
            await log_dm_sent(message.channel.recipient, message.content)
        return
    
    # Log DMs received
    if isinstance(message.channel, discord.DMChannel):
        await log_dm_received(message)

async def global_on_guild_join(guild):
    """Global guild join handler"""
    await log_guild_join_global(guild)

async def global_on_guild_remove(guild):
    """Global guild remove handler"""
    await log_guild_remove_global(guild)

async def global_on_app_command_error(interaction, error):
    """Global app command error handler"""
    await log_command_error(interaction, error)

async def global_on_command_error(ctx, error):
    """Global command error handler"""
    await log_command_error(ctx, error)

def hook_into_events():
    """Hook into existing bot events without overriding them"""
    # Add global logging to existing events by adding listeners
    bot.add_listener(global_on_message, 'on_message')
    bot.add_listener(global_on_guild_join, 'on_guild_join')
    bot.add_listener(global_on_guild_remove, 'on_guild_remove')
    bot.add_listener(global_on_app_command_error, 'on_app_command_error')
    bot.add_listener(global_on_command_error, 'on_command_error')
    
    print("✅ Global logging event hooks installed")

# Function to initialize global logging
async def initialize_global_logging():
    """Initialize global logging system"""
    await setup_global_channels()
    hook_into_events()
    
    # Log bot startup
    await log_console_event("Bot Startup", f"✅ VAAZHA Bot started successfully!\n**Servers:** {len(bot.guilds)}\n**Commands:** {len(bot.tree.get_commands())}")

print("✅ Global logging system loaded")
