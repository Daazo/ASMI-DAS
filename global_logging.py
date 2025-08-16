
import discord
from discord.ext import commands
import asyncio
from datetime import datetime
import os
from main import bot, get_server_data

# ==== GLOBAL LOGGING CONFIGURATION ====
SUPPORT_SERVER_ID = int(os.getenv('SUPPORT_SERVER_ID', '0'))  # Set this in your secrets
LOG_CATEGORY_ID = int(os.getenv('LOG_CATEGORY_ID', '0'))      # Set this in your secrets

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
        "security-alerts",
        "economy-global",
        "karma-global"
    ]
    
    for channel_name in global_channels:
        await get_or_create_global_channel(channel_name)
    
    # Create per-server channels for existing guilds
    for guild in bot.guilds:
        if guild.id != SUPPORT_SERVER_ID:  # Don't create logs for support server itself
            channel_name = f"server-{guild.id}-{guild.name}".replace(" ", "-").lower()[:100]  # Discord limit
            await get_or_create_global_channel(channel_name)
    
    print(f"✅ Global logging system initialized with {len(global_log_channels)} channels")

# Event handlers for global logging
@bot.event
async def on_message_global_log(message):
    """Log DMs and important messages globally"""
    if message.author.bot:
        return
    
    # === DM sent TO bot ===
    if isinstance(message.channel, discord.DMChannel):
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

@bot.event  
async def on_bot_dm_send(recipient, content):
    """Log DMs sent by bot"""
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

@bot.event
async def on_command_error_global(ctx, error):
    """Log command errors globally"""
    embed = discord.Embed(
        title="❌ Command Error",
        description=f"**Guild:** {ctx.guild.name if ctx.guild else 'DM'} ({ctx.guild.id if ctx.guild else 'N/A'})\n"
                   f"**User:** {ctx.author} ({ctx.author.id})\n"
                   f"**Command:** {ctx.command}\n"
                   f"**Error:** {str(error)[:1000]}",
        color=0xe74c3c,
        timestamp=datetime.now()
    )
    embed.set_footer(text=f"Error Type: {type(error).__name__}")
    await log_to_global("command-errors", embed)

@bot.event
async def on_guild_join_global(guild):
    """Create per-guild channel when bot joins new server"""
    # Create guild-specific log channel
    channel_name = f"server-{guild.id}-{guild.name}".replace(" ", "-").lower()[:100]
    await get_or_create_global_channel(channel_name)
    
    # Log the join event
    embed = discord.Embed(
        title="🎉 Bot Joined New Server",
        description=f"**Server:** {guild.name}\n**ID:** {guild.id}\n**Owner:** {guild.owner}\n**Members:** {guild.member_count}",
        color=0x43b581,
        timestamp=datetime.now()
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    await log_to_global("bot-events", embed)

@bot.event 
async def on_guild_remove_global(guild):
    """Handle bot leaving server"""
    # Log the leave event
    embed = discord.Embed(
        title="👋 Bot Left Server",
        description=f"**Server:** {guild.name}\n**ID:** {guild.id}\n**Members:** {guild.member_count}",
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
    
    # Route to appropriate channel based on activity type
    if "economy" in activity_type.lower():
        await log_to_global("economy-global", embed)
    elif "karma" in activity_type.lower():
        await log_to_global("karma-global", embed)
    elif "security" in activity_type.lower():
        await log_to_global("security-alerts", embed)
    else:
        await log_to_global("live-console", embed)

async def log_per_server_activity(guild_id: int, activity: str):
    """Log activity to per-server channel"""
    guild = bot.get_guild(guild_id)
    if not guild or guild.id == SUPPORT_SERVER_ID:
        return
    
    channel_name = f"server-{guild.id}-{guild.name}".replace(" ", "-").lower()[:100]
    
    embed = discord.Embed(
        title="📊 Server Activity",
        description=activity,
        color=0x3498db,
        timestamp=datetime.now()
    )
    embed.set_footer(text=f"Server: {guild.name}")
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    await log_to_global(channel_name, embed)

# Hook into bot events
original_on_message = None
original_on_guild_join = None
original_on_guild_remove = None

# Try to get existing listeners
listeners = bot.extra_events.get('on_message', [])
if listeners:
    original_on_message = listeners[0]

listeners = bot.extra_events.get('on_guild_join', [])  
if listeners:
    original_on_guild_join = listeners[0]

listeners = bot.extra_events.get('on_guild_remove', [])
if listeners:
    original_on_guild_remove = listeners[0]

@bot.event
async def on_message(message):
    # Call original handler first
    if original_on_message:
        await original_on_message(message)
    
    # Then our global logging
    await on_message_global_log(message)

@bot.event  
async def on_guild_join(guild):
    # Call original handler first
    if original_on_guild_join:
        await original_on_guild_join(guild)
    
    # Then our global logging
    await on_guild_join_global(guild)

@bot.event
async def on_guild_remove(guild):
    # Call original handler first  
    if original_on_guild_remove:
        await original_on_guild_remove(guild)
    
    # Then our global logging
    await on_guild_remove_global(guild)

# Add to bot ready event
async def initialize_global_logging():
    """Initialize global logging system"""
    await setup_global_channels()

print("✅ Global logging system loaded")
