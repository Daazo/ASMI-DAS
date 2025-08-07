
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import aiohttp
import time
import os
import re
import random
from datetime import datetime, timedelta
import motor.motor_asyncio
from typing import Optional, Union
import json
from PIL import Image, ImageDraw, ImageFont
import io
import requests

# Bot configuration
BOT_NAME = "ᴠᴀᴀᴢʜᴀ"
BOT_TAGLINE = "𝓨𝓸𝓾𝓻 𝓯𝓻𝓲𝓮𝓷𝓭𝓵𝔂 𝓼𝓮𝓻𝓿𝓮𝓻 𝓪𝓼𝓼𝓲𝓼𝓽𝓪𝓷𝓽 𝓯𝓻𝓸𝓶 𝓖𝓸𝓭'𝓼 𝓞𝔀𝓷 𝓒𝓸𝓾𝓷𝓽𝓻𝔂 🌴"
BOT_OWNER_NAME = "Daazo|Rio"
BOT_OWNER_DESCRIPTION = "Creator and developer of ᴠᴀᴀᴢʜᴀ bot. Passionate developer from Kerala, India."

# MongoDB setup
MONGO_URI = os.getenv('MONGO_URI')
if MONGO_URI:
    mongo_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
    db = mongo_client.vaazha_bot
else:
    mongo_client = None
    db = None

# Cache for server settings
server_cache = {}

async def get_prefix(bot, message):
    """Get custom prefix for server"""
    if not message.guild:
        return '!'
    
    guild_id = str(message.guild.id)
    if guild_id in server_cache and 'prefix' in server_cache[guild_id]:
        return server_cache[guild_id]['prefix']
    
    if db is not None:
        server_data = await db.servers.find_one({'guild_id': guild_id})
        if server_data and 'prefix' in server_data:
            if guild_id not in server_cache:
                server_cache[guild_id] = {}
            server_cache[guild_id]['prefix'] = server_data['prefix']
            return server_data['prefix']
    
    return '!'

# Bot setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=get_prefix, intents=intents, case_insensitive=True)
bot.remove_command('help')
bot.start_time = time.time()

async def get_server_data(guild_id):
    """Get server configuration from database"""
    guild_id = str(guild_id)
    if db is not None:
        return await db.servers.find_one({'guild_id': guild_id}) or {}
    return {}

async def update_server_data(guild_id, data):
    """Update server configuration in database"""
    guild_id = str(guild_id)
    if db is not None:
        await db.servers.update_one(
            {'guild_id': guild_id},
            {'$set': data},
            upsert=True
        )
    # Update cache
    if guild_id not in server_cache:
        server_cache[guild_id] = {}
    server_cache[guild_id].update(data)

async def log_action(guild_id, log_type, message):
    """Log actions to appropriate channels"""
    server_data = await get_server_data(guild_id)
    log_channels = server_data.get('log_channels', {})
    
    # Send to specific log channel if set
    if log_type in log_channels:
        channel = bot.get_channel(int(log_channels[log_type]))
        if channel:
            await channel.send(embed=discord.Embed(description=message, color=0x3498db))
    
    # Send to combined logs if set
    if 'all' in log_channels:
        channel = bot.get_channel(int(log_channels['all']))
        if channel:
            await channel.send(embed=discord.Embed(description=message, color=0x3498db))

async def has_permission(interaction, permission_level):
    """Check if user has required permission level"""
    if interaction.user.id == interaction.guild.owner_id:
        return True
    
    server_data = await get_server_data(interaction.guild.id)
    
    if permission_level == "main_moderator":
        main_mod_role_id = server_data.get('main_moderator_role')
        if main_mod_role_id:
            main_mod_role = interaction.guild.get_role(int(main_mod_role_id))
            return main_mod_role in interaction.user.roles
    
    elif permission_level == "junior_moderator":
        # Junior mods can access if they have junior role OR main role
        junior_mod_role_id = server_data.get('junior_moderator_role')
        main_mod_role_id = server_data.get('main_moderator_role')
        
        if junior_mod_role_id:
            junior_mod_role = interaction.guild.get_role(int(junior_mod_role_id))
            if junior_mod_role in interaction.user.roles:
                return True
        
        if main_mod_role_id:
            main_mod_role = interaction.guild.get_role(int(main_mod_role_id))
            if main_mod_role in interaction.user.roles:
                return True
    
    return False

# XP System Functions
async def add_xp(user_id, guild_id, amount):
    """Add XP to user"""
    if db is None:
        return
    
    user_data = await db.users.find_one({'user_id': str(user_id), 'guild_id': str(guild_id)})
    if not user_data:
        user_data = {'user_id': str(user_id), 'guild_id': str(guild_id), 'xp': 0, 'level': 1, 'last_xp_gain': 0}
    
    # Check cooldown (60 seconds)
    current_time = time.time()
    if current_time - user_data.get('last_xp_gain', 0) < 60:
        return False
    
    user_data['xp'] += amount
    user_data['last_xp_gain'] = current_time
    
    # Calculate new level
    old_level = user_data.get('level', 1)
    new_level = calculate_level(user_data['xp'])
    level_up = new_level > old_level
    user_data['level'] = new_level
    
    await db.users.update_one(
        {'user_id': str(user_id), 'guild_id': str(guild_id)},
        {'$set': user_data},
        upsert=True
    )
    
    return level_up

def calculate_level(xp):
    """Calculate level based on XP"""
    return int((xp / 100) ** 0.5) + 1

def xp_for_level(level):
    """Calculate XP required for level"""
    return ((level - 1) ** 2) * 100

async def create_rank_image(user, xp, level, rank=None):
    """Create rank card image"""
    try:
        # Create image
        img = Image.new('RGB', (800, 200), color='#2f3136')
        draw = ImageDraw.Draw(img)
        
        # Download user avatar
        avatar_response = requests.get(str(user.display_avatar.url))
        avatar = Image.open(io.BytesIO(avatar_response.content)).resize((150, 150))
        
        # Paste avatar
        img.paste(avatar, (25, 25))
        
        # Draw text
        draw.text((200, 30), user.display_name, fill='white', font_size=30)
        draw.text((200, 70), f"Level {level}", fill='#7289da', font_size=25)
        draw.text((200, 110), f"XP: {xp}/{xp_for_level(level + 1)}", fill='white', font_size=20)
        
        if rank:
            draw.text((200, 140), f"Rank: #{rank}", fill='#43b581', font_size=20)
        
        # Save to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        return img_bytes
    except:
        return None

# Bot Events
@bot.event
async def on_ready():
    print(f'{bot.user} has landed in Kerala! 🌴')
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(bot.guilds)} servers"
        )
    )
    
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.event
async def on_guild_join(guild):
    """Update presence when joining new server"""
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(bot.guilds)} servers"
        )
    )

@bot.event
async def on_guild_remove(guild):
    """Update presence when leaving server"""
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(bot.guilds)} servers"
        )
    )

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Check for bot owner mention
    owner_id = os.getenv('BOT_OWNER_ID')
    if owner_id and f"<@{owner_id}>" in message.content:
        embed = discord.Embed(
            title="😎 That's my Dev!",
            description=f"This awesome bot was crafted by <@{owner_id}>\nTreat him well – without him, I wouldn't even exist! 🤖💙",
            color=0x3498db
        )
        embed.add_field(name="Developer", value=BOT_OWNER_NAME, inline=True)
        embed.add_field(name="About", value=BOT_OWNER_DESCRIPTION, inline=False)
        await message.channel.send(embed=embed)
    
    # Bot mention reply
    if bot.user in message.mentions and not message.content.startswith('/'):
        embed = discord.Embed(
            title="👋 Heya! I'm your assistant bot 🤖",
            description="Need help? Try using `/help` to explore my features.\nModerators can use setup commands too!\n\nLet's make this server awesome together 💫",
            color=0x3498db
        )
        
        view = discord.ui.View()
        help_button = discord.ui.Button(label="📜 Commands", style=discord.ButtonStyle.primary)
        help_button.callback = lambda i: help_command_callback(i)
        view.add_item(help_button)
        
        await message.channel.send(embed=embed, view=view)
    
    # XP System
    if message.guild:
        xp_gain = random.randint(5, 15)
        level_up = await add_xp(message.author.id, message.guild.id, xp_gain)
        
        if level_up:
            server_data = await get_server_data(message.guild.id)
            xp_channel_id = server_data.get('xp_channel')
            
            if xp_channel_id:
                xp_channel = bot.get_channel(int(xp_channel_id))
                if xp_channel:
                    user_data = await db.users.find_one({'user_id': str(message.author.id), 'guild_id': str(message.guild.id)})
                    level = user_data.get('level', 1)
                    
                    embed = discord.Embed(
                        title="🎉 Level Up!",
                        description=f"{message.author.mention} reached **Level {level}**!",
                        color=0xf39c12
                    )
                    
                    # Try to create rank image
                    rank_image = await create_rank_image(message.author, user_data.get('xp', 0), level)
                    if rank_image:
                        file = discord.File(rank_image, filename="levelup.png")
                        embed.set_image(url="attachment://levelup.png")
                        await xp_channel.send(embed=embed, file=file)
                    else:
                        await xp_channel.send(embed=embed)
    
    await bot.process_commands(message)

# Command error handler for automatic help
@bot.event
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handle slash command errors and provide help"""
    if isinstance(error, app_commands.MissingPermissions):
        embed = discord.Embed(
            title="❌ **Missing Permissions**",
            description="You don't have the required permissions to use this command!",
            color=0xe74c3c
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    elif isinstance(error, app_commands.CommandOnCooldown):
        embed = discord.Embed(
            title="⏳ **Command on Cooldown**",
            description=f"Please wait {error.retry_after:.2f} seconds before using this command again!",
            color=0xf39c12
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    else:
        # Get command help information
        command_name = interaction.command.name if interaction.command else "unknown"
        await send_command_help(interaction, command_name)

async def send_command_help(interaction: discord.Interaction, command_name: str):
    """Send detailed help for specific command"""
    command_help = {
        "kick": {
            "title": "👢 **KICK Command Help**",
            "description": "**Usage:** `/kick @user [reason]`\n\n**What it does:** Removes a user from the server\n**Permission:** 🔴 Main Moderator only\n\n**Example:** `/kick @BadUser Breaking rules`",
            "color": 0xe74c3c
        },
        "ban": {
            "title": "🔨 **BAN Command Help**",
            "description": "**Usage:** `/ban @user [reason]`\n\n**What it does:** Permanently bans a user from the server\n**Permission:** 🔴 Main Moderator only\n\n**Example:** `/ban @Spammer Repeated spam messages`",
            "color": 0xe74c3c
        },
        "mute": {
            "title": "🔇 **MUTE Command Help**",
            "description": "**Usage:** `/mute @user`\n\n**What it does:** Mutes a user in voice channel\n**Permission:** 🔵 Junior Moderator+\n\n**Example:** `/mute @NoisyUser`",
            "color": 0xf39c12
        },
        "unmute": {
            "title": "🔊 **UNMUTE Command Help**",
            "description": "**Usage:** `/unmute @user`\n\n**What it does:** Unmutes a user in voice channel\n**Permission:** 🔵 Junior Moderator+\n\n**Example:** `/unmute @User`",
            "color": 0x43b581
        },
        "say": {
            "title": "💬 **SAY Command Help**",
            "description": "**Usage:** `/say message:\"text\" [channel:#channel]`\n\n**What it does:** Makes the bot say something\n**Permission:** 🔵 Junior Moderator+\n\n**Example:** `/say message:\"Hello everyone!\" channel:#general`",
            "color": 0x9b59b6
        },
        "embed": {
            "title": "📋 **EMBED Command Help**",
            "description": "**Usage:** `/embed title:\"Title\" description:\"Text\" [color:blue]`\n\n**What it does:** Sends a rich embedded message\n**Permission:** 🔵 Junior Moderator+\n\n**Example:** `/embed title:\"Rules\" description:\"Be nice to everyone!\" color:green`",
            "color": 0x3498db
        },
        "announce": {
            "title": "📢 **ANNOUNCE Command Help**",
            "description": "**Usage:** `/announce channel:#channel message:\"text\" [mention:@role]`\n\n**What it does:** Sends official server announcements\n**Permission:** 🔴 Main Moderator only\n\n**Example:** `/announce channel:#announcements message:\"Server update!\" mention:@everyone`",
            "color": 0xf39c12
        },
        "poll": {
            "title": "📊 **POLL Command Help**",
            "description": "**Usage:** `/poll question:\"Question?\" option1:\"Yes\" option2:\"No\" [option3] [option4]`\n\n**What it does:** Creates interactive polls with reactions\n**Permission:** 🔵 Junior Moderator+\n\n**Example:** `/poll question:\"Pizza party?\" option1:\"Yes!\" option2:\"No\"`",
            "color": 0x43b581
        },
        "setup": {
            "title": "⚙️ **SETUP Command Help**",
            "description": "**Usage:** `/setup <action> [value] [channel] [role]`\n\n**Actions:**\n• `main_moderator` - Set main mod role\n• `junior_moderator` - Set junior mod role\n• `welcome` - Configure welcome messages\n• `prefix` - Set custom prefix\n• `logs` - Set log channels\n• `xp` - Set XP announcement channel\n\n**Permission:** 🔴 Main Moderator (main_moderator: Server Owner only)\n\n**Example:** `/setup welcome channel:#welcome value:\"Welcome {user}!\"`",
            "color": 0xf39c12
        },
        "nuke": {
            "title": "💥 **NUKE Command Help**",
            "description": "**Usage:** `/nuke`\n\n**What it does:** Deletes ALL messages in current channel (irreversible!)\n**Permission:** 🔴 Main Moderator only\n\n**⚠️ WARNING:** This action cannot be undone!\n\n**Example:** `/nuke`",
            "color": 0xe74c3c
        },
        "movevc": {
            "title": "🔀 **MOVEVC Command Help**",
            "description": "**Usage:** `/movevc @user #voice-channel`\n\n**What it does:** Moves user from one voice channel to another\n**Permission:** 🔵 Junior Moderator+\n\n**Example:** `/movevc @User #General`",
            "color": 0x3498db
        },
        "vckick": {
            "title": "👢 **VCKICK Command Help**",
            "description": "**Usage:** `/vckick @user`\n\n**What it does:** Kicks user from their current voice channel\n**Permission:** 🔵 Junior Moderator+\n\n**Example:** `/vckick @NoisyUser`",
            "color": 0xf39c12
        },
        "vclock": {
            "title": "🔒 **VCLOCK Command Help**",
            "description": "**Usage:** `/vclock`\n\n**What it does:** Locks your current voice channel (prevents new joins)\n**Permission:** 🔵 Junior Moderator+\n\n**Note:** You must be in a voice channel\n\n**Example:** `/vclock`",
            "color": 0xe74c3c
        },
        "vcunlock": {
            "title": "🔓 **VCUNLOCK Command Help**",
            "description": "**Usage:** `/vcunlock`\n\n**What it does:** Unlocks your current voice channel\n**Permission:** 🔵 Junior Moderator+\n\n**Note:** You must be in a voice channel\n\n**Example:** `/vcunlock`",
            "color": 0x43b581
        },
        "vclimit": {
            "title": "🔢 **VCLIMIT Command Help**",
            "description": "**Usage:** `/vclimit <number>`\n\n**What it does:** Sets user limit for your current voice channel\n**Permission:** 🔵 Junior Moderator+\n**Range:** 0-99 (0 = unlimited)\n\n**Note:** You must be in a voice channel\n\n**Example:** `/vclimit 10`",
            "color": 0x3498db
        },
        "rank": {
            "title": "📊 **RANK Command Help**",
            "description": "**Usage:** `/rank [user:@user]`\n\n**What it does:** Shows XP rank card with level, XP, and server ranking\n**Permission:** 🟢 Everyone\n\n**Example:** `/rank` or `/rank user:@Someone`",
            "color": 0x43b581
        },
        "leaderboard": {
            "title": "🏆 **LEADERBOARD Command Help**",
            "description": "**Usage:** `/leaderboard`\n\n**What it does:** Displays top 10 users by XP with rankings\n**Permission:** 🟢 Everyone\n\n**Example:** `/leaderboard`",
            "color": 0xf39c12
        }
    }
    
    if command_name.lower() in command_help:
        help_info = command_help[command_name.lower()]
        embed = discord.Embed(
            title=help_info["title"],
            description=help_info["description"],
            color=help_info["color"]
        )
        embed.set_footer(text="🟢 = Everyone • 🔵 = Junior Moderator • 🔴 = Main Moderator")
        
        try:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except:
            try:
                await interaction.followup.send(embed=embed, ephemeral=True)
            except:
                pass
    else:
        embed = discord.Embed(
            title="❓ **Command Help**",
            description=f"Use `/help` to see all available commands!\n\n**Tip:** Type `/help` and click the category buttons for detailed command information.",
            color=0x3498db
        )
        try:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except:
            try:
                await interaction.followup.send(embed=embed, ephemeral=True)
            except:
                pass

@bot.event
async def on_member_join(member):
    """Send welcome message and DM"""
    server_data = await get_server_data(member.guild.id)
    
    # Send welcome message to channel
    welcome_channel_id = server_data.get('welcome_channel')
    welcome_message = server_data.get('welcome_message', f"Welcome to {member.guild.name}!")
    
    if welcome_channel_id:
        welcome_channel = bot.get_channel(int(welcome_channel_id))
        if welcome_channel:
            embed = discord.Embed(
                title="👋 Welcome!",
                description=welcome_message.format(user=member.mention, server=member.guild.name),
                color=0x43b581
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await welcome_channel.send(embed=embed)
    
    # Send DM to new member
    try:
        embed = discord.Embed(
            title=f"👋 Hii, I'm **{BOT_NAME}** – your helpful assistant!",
            description=f"Welcome to **{member.guild.name}** 🎊\nWe're thrilled to have you here!\n\nGet comfy, explore the channels, and feel free to say hi 👀\nIf you ever need help, just mention me or use a command!\n\nLet's make this server even more awesome together 💫",
            color=0x3498db
        )
        
        view = discord.ui.View()
        invite_button = discord.ui.Button(label="🤖 Invite Bot", style=discord.ButtonStyle.link, url=f"https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot%20applications.commands")
        view.add_item(invite_button)
        
        await member.send(embed=embed, view=view)
    except:
        pass  # User has DMs disabled

@bot.event
async def on_member_remove(member):
    """Send goodbye DM"""
    try:
        embed = discord.Embed(
            title=f"Hey {member.display_name}, we noticed you left **{member.guild.name}** 😔",
            description=f"Just wanted to say thank you for being a part of our community.\nWe hope you had a good time there, and we'll always have a spot saved if you return 💙\n\nTake care and stay awesome! ✨\n— {BOT_NAME}",
            color=0xe74c3c
        )
        
        view = discord.ui.View()
        invite_button = discord.ui.Button(label="🤖 Invite Bot", style=discord.ButtonStyle.link, url=f"https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot%20applications.commands")
        view.add_item(invite_button)
        
        await member.send(embed=embed, view=view)
    except:
        pass  # User has DMs disabled

# Help Command Callback
async def help_command_callback(interaction):
    """Callback for help button"""
    embed = discord.Embed(
        title="🤖 **ᴠᴀᴀᴢʜᴀ** Help Center",
        description=f"**✨ Namaskaram! Need help? ✨**\n\n**🌴 ᴠᴀᴀᴢʜᴀ-ʙᴏᴛ undu. Chill aanu! 🌴**\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n📋 **Select a category below to explore all commands**\n🛠 **Use `/setup` commands to configure bot per server**\n💬 **Type any command for instant usage help!**\n\n🔐 **Permission Levels:**\n🟢 **Everyone** - All server members\n🔵 **Junior Moderator** - Limited moderation access  \n🔴 **Main Moderator** - Full access (Server Owner level)\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        color=0x3498db
    )
    embed.set_footer(text=f"🌴 {BOT_TAGLINE}", icon_url=bot.user.display_avatar.url)
    
    view = HelpView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# Help View Class
class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__()
    
    @discord.ui.button(label="🧩 General", style=discord.ButtonStyle.primary, emoji="🧩")
    async def general_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🧩 **General Commands**",
            description="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=0x3498db
        )
        embed.add_field(
            name="🟢 `/help`", 
            value="**Usage:** `/help`\n**Description:** Show comprehensive help menu with all commands", 
            inline=False
        )
        embed.add_field(
            name="🟢 `/userinfo`", 
            value="**Usage:** `/userinfo [user]`\n**Description:** Display detailed user information, join date, roles, etc.", 
            inline=False
        )
        embed.add_field(
            name="🟢 `/serverinfo`", 
            value="**Usage:** `/serverinfo`\n**Description:** Show server details like owner, member count, creation date", 
            inline=False
        )
        embed.add_field(
            name="🔵 `/ping`", 
            value="**Usage:** `/ping`\n**Description:** Check bot latency and connection status", 
            inline=False
        )
        embed.add_field(
            name="🔵 `/uptime`", 
            value="**Usage:** `/uptime`\n**Description:** Display how long the bot has been running", 
            inline=False
        )
        embed.set_footer(text="🟢 = Everyone • 🔵 = Junior Moderator • 🔴 = Main Moderator")
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="🛡 Moderation", style=discord.ButtonStyle.danger, emoji="🛡")
    async def moderation_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🛡 **Moderation Commands**",
            description="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=0xe74c3c
        )
        embed.add_field(
            name="🔴 `/kick`", 
            value="**Usage:** `/kick @user [reason]`\n**Description:** Remove a user from the server with optional reason", 
            inline=False
        )
        embed.add_field(
            name="🔴 `/ban`", 
            value="**Usage:** `/ban @user [reason]`\n**Description:** Permanently ban a user from the server", 
            inline=False
        )
        embed.add_field(
            name="🔴 `/nuke`", 
            value="**Usage:** `/nuke`\n**Description:** Delete ALL messages in current channel (irreversible!)", 
            inline=False
        )
        embed.add_field(
            name="🔵 `/mute`", 
            value="**Usage:** `/mute @user`\n**Description:** Mute user in voice channel", 
            inline=False
        )
        embed.add_field(
            name="🔵 `/unmute`", 
            value="**Usage:** `/unmute @user`\n**Description:** Unmute user in voice channel", 
            inline=False
        )
        embed.add_field(
            name="🔵 Voice Commands", 
            value="**`/movevc @user #channel`** - Move user to voice channel\n**`/vckick @user`** - Kick user from voice\n**`/vclock`** - Lock current voice channel\n**`/vcunlock`** - Unlock voice channel\n**`/vclimit <number>`** - Set voice channel limit", 
            inline=False
        )
        embed.set_footer(text="🟢 = Everyone • 🔵 = Junior Moderator • 🔴 = Main Moderator")
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="🛠 Setup", style=discord.ButtonStyle.secondary, emoji="🛠")
    async def setup_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🛠 **Setup Commands**",
            description="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=0xf39c12
        )
        embed.add_field(
            name="🔴 `/setup main_moderator`", 
            value="**Usage:** `/setup main_moderator role:@role`\n**Description:** Set main moderator role (Server Owner only)", 
            inline=False
        )
        embed.add_field(
            name="🔴 `/setup junior_moderator`", 
            value="**Usage:** `/setup junior_moderator role:@role`\n**Description:** Set junior moderator role", 
            inline=False
        )
        embed.add_field(
            name="🔴 `/setup welcome`", 
            value="**Usage:** `/setup welcome channel:#channel value:\"message\"`\n**Description:** Configure welcome messages and channel", 
            inline=False
        )
        embed.add_field(
            name="🔴 `/setup prefix`", 
            value="**Usage:** `/setup prefix value:!`\n**Description:** Set custom command prefix for server", 
            inline=False
        )
        embed.add_field(
            name="🔴 `/setup logs`", 
            value="**Usage:** `/setup logs value:moderation channel:#logs`\n**Description:** Configure logging channels (all, moderation, xp, etc.)", 
            inline=False
        )
        embed.add_field(
            name="🔴 `/setup xp`", 
            value="**Usage:** `/setup xp channel:#xp-logs`\n**Description:** Set XP level-up announcement channel", 
            inline=False
        )
        embed.set_footer(text="🟢 = Everyone • 🔵 = Junior Moderator • 🔴 = Main Moderator")
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="📣 Communication", style=discord.ButtonStyle.secondary, emoji="📣")
    async def communication_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📣 **Communication Commands**",
            description="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=0x9b59b6
        )
        embed.add_field(
            name="🔵 `/say`", 
            value="**Usage:** `/say message:\"text\" [channel:#channel]`\n**Description:** Make bot send a message", 
            inline=False
        )
        embed.add_field(
            name="🔵 `/embed`", 
            value="**Usage:** `/embed title:\"Title\" description:\"Text\" [color:blue]`\n**Description:** Send rich embedded message with custom styling", 
            inline=False
        )
        embed.add_field(
            name="🔴 `/announce`", 
            value="**Usage:** `/announce channel:#channel message:\"text\" [mention:@role]`\n**Description:** Send official server announcements", 
            inline=False
        )
        embed.add_field(
            name="🔵 `/poll`", 
            value="**Usage:** `/poll question:\"Question?\" option1:\"Yes\" option2:\"No\"`\n**Description:** Create interactive polls with reactions", 
            inline=False
        )
        embed.add_field(
            name="🔵 `/reminder`", 
            value="**Usage:** `/reminder message:\"text\" time:1h30m`\n**Description:** Set personal reminders (format: 1h30m, 45s, 2d)", 
            inline=False
        )
        embed.add_field(
            name="🔴 `/dm`", 
            value="**Usage:** `/dm user:@user message:\"text\"`\n**Description:** Send DM to user from server", 
            inline=False
        )
        embed.set_footer(text="🟢 = Everyone • 🔵 = Junior Moderator • 🔴 = Main Moderator")
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="📊 XP System", style=discord.ButtonStyle.success, emoji="📊")
    async def xp_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📊 **XP & Leveling System**",
            description="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=0x43b581
        )
        embed.add_field(
            name="🟢 `/rank`", 
            value="**Usage:** `/rank [user:@user]`\n**Description:** Show XP rank card with level, XP, and server ranking", 
            inline=False
        )
        embed.add_field(
            name="🟢 `/leaderboard`", 
            value="**Usage:** `/leaderboard`\n**Description:** Display top 10 users by XP with rankings", 
            inline=False
        )
        embed.add_field(
            name="💡 **How XP Works**", 
            value="• Gain 5-15 XP per message (60s cooldown)\n• Level up formula: `√(XP/100) + 1`\n• Level announcements in configured channel\n• Beautiful rank cards with avatars", 
            inline=False
        )
        embed.set_footer(text="🟢 = Everyone • 🔵 = Junior Moderator • 🔴 = Main Moderator")
        await interaction.response.edit_message(embed=embed, view=self)

# Slash Commands
@bot.tree.command(name="help", description="Show help menu with all commands")
async def help_command(interaction: discord.Interaction):
    await help_command_callback(interaction)

@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    if not await has_permission(interaction, "junior_moderator"):
        await interaction.response.send_message("❌ You need Junior Moderator permissions to use this command!", ephemeral=True)
        return
    
    latency = round(bot.latency * 1000)
    embed = discord.Embed(title="🏓 Pong!", description=f"Latency: {latency}ms", color=0x43b581)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="uptime", description="Show bot uptime")
async def uptime(interaction: discord.Interaction):
    if not await has_permission(interaction, "junior_moderator"):
        await interaction.response.send_message("❌ You need Junior Moderator permissions to use this command!", ephemeral=True)
        return
    
    uptime_seconds = time.time() - bot.start_time
    uptime_str = str(timedelta(seconds=int(uptime_seconds)))
    
    embed = discord.Embed(title="⏰ Bot Uptime", description=f"I've been running for: **{uptime_str}**", color=0x3498db)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="userinfo", description="Show information about a user")
async def userinfo(interaction: discord.Interaction, user: discord.Member = None):
    if user is None:
        user = interaction.user
    
    embed = discord.Embed(title=f"👤 {user.display_name}", color=user.color)
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="📅 Joined Server", value=user.joined_at.strftime("%B %d, %Y"), inline=True)
    embed.add_field(name="📅 Account Created", value=user.created_at.strftime("%B %d, %Y"), inline=True)
    embed.add_field(name="🎭 Roles", value=f"{len(user.roles)-1} roles", inline=True)
    embed.add_field(name="🆔 User ID", value=user.id, inline=True)
    embed.add_field(name="📱 Status", value=str(user.status).title(), inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="serverinfo", description="Show server information")
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    
    embed = discord.Embed(title=f"🏰 {guild.name}", color=0x3498db)
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.add_field(name="👑 Owner", value=guild.owner.mention, inline=True)
    embed.add_field(name="👥 Members", value=guild.member_count, inline=True)
    embed.add_field(name="📅 Created", value=guild.created_at.strftime("%B %d, %Y"), inline=True)
    embed.add_field(name="🔒 Verification Level", value=str(guild.verification_level).title(), inline=True)
    embed.add_field(name="📂 Channels", value=len(guild.channels), inline=True)
    embed.add_field(name="🎭 Roles", value=len(guild.roles), inline=True)
    embed.add_field(name="🆔 Server ID", value=guild.id, inline=True)
    
    await interaction.response.send_message(embed=embed)

# Import command modules
from setup_commands import *
from moderation_commands import *
from communication_commands import *
from xp_commands import *

# Try to import voice commands
try:
    from voice_commands import *
except ImportError:
    print("Voice commands module not found, skipping...")

# Run the bot
if __name__ == "__main__":
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("Please set DISCORD_BOT_TOKEN in your secrets!")
    else:
        bot.run(token)
