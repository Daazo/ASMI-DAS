
import discord
from discord.ext import commands
from discord import app_commands
from main import bot, has_permission, log_action

@bot.tree.command(name="movevc", description="Move user to different voice channel")
@app_commands.describe(user="User to move", channel="Voice channel to move to")
async def movevc(interaction: discord.Interaction, user: discord.Member, channel: discord.VoiceChannel):
    if not await has_permission(interaction, "junior_moderator"):
        await interaction.response.send_message("❌ You need Junior Moderator permissions to use this command!", ephemeral=True)
        return
    
    if not user.voice:
        await interaction.response.send_message("❌ User is not in a voice channel!", ephemeral=True)
        return
    
    try:
        await user.move_to(channel)
        
        embed = discord.Embed(
            title="🔀 User Moved",
            description=f"**User:** {user.mention}\n**Moved to:** {channel.mention}\n**Moderator:** {interaction.user.mention}",
            color=0x43b581
        )
        await interaction.response.send_message(embed=embed)
        
        await log_action(interaction.guild.id, "moderation", f"🛡 [MOVE VC] {user} moved to {channel.name} by {interaction.user}")
    
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to move this user!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="vckick", description="Kick user from voice channel")
@app_commands.describe(user="User to kick from voice")
async def vckick(interaction: discord.Interaction, user: discord.Member):
    if not await has_permission(interaction, "junior_moderator"):
        await interaction.response.send_message("❌ You need Junior Moderator permissions to use this command!", ephemeral=True)
        return
    
    if not user.voice:
        await interaction.response.send_message("❌ User is not in a voice channel!", ephemeral=True)
        return
    
    try:
        await user.move_to(None)
        
        embed = discord.Embed(
            title="👢 User Kicked from VC",
            description=f"**User:** {user.mention}\n**Moderator:** {interaction.user.mention}",
            color=0xf39c12
        )
        await interaction.response.send_message(embed=embed)
        
        await log_action(interaction.guild.id, "moderation", f"🛡 [VC KICK] {user} kicked from voice by {interaction.user}")
    
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to disconnect this user!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="vclock", description="Lock current voice channel")
async def vclock(interaction: discord.Interaction):
    if not await has_permission(interaction, "junior_moderator"):
        await interaction.response.send_message("❌ You need Junior Moderator permissions to use this command!", ephemeral=True)
        return
    
    if not interaction.user.voice:
        await interaction.response.send_message("❌ You need to be in a voice channel to use this command!", ephemeral=True)
        return
    
    channel = interaction.user.voice.channel
    
    try:
        await channel.set_permissions(interaction.guild.default_role, connect=False)
        
        embed = discord.Embed(
            title="🔒 Voice Channel Locked",
            description=f"**Channel:** {channel.mention}\n**Moderator:** {interaction.user.mention}",
            color=0xe74c3c
        )
        await interaction.response.send_message(embed=embed)
        
        await log_action(interaction.guild.id, "moderation", f"🛡 [VC LOCK] {channel.name} locked by {interaction.user}")
    
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to modify this channel!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="vcunlock", description="Unlock current voice channel")
async def vcunlock(interaction: discord.Interaction):
    if not await has_permission(interaction, "junior_moderator"):
        await interaction.response.send_message("❌ You need Junior Moderator permissions to use this command!", ephemeral=True)
        return
    
    if not interaction.user.voice:
        await interaction.response.send_message("❌ You need to be in a voice channel to use this command!", ephemeral=True)
        return
    
    channel = interaction.user.voice.channel
    
    try:
        await channel.set_permissions(interaction.guild.default_role, connect=None)
        
        embed = discord.Embed(
            title="🔓 Voice Channel Unlocked",
            description=f"**Channel:** {channel.mention}\n**Moderator:** {interaction.user.mention}",
            color=0x43b581
        )
        await interaction.response.send_message(embed=embed)
        
        await log_action(interaction.guild.id, "moderation", f"🛡 [VC UNLOCK] {channel.name} unlocked by {interaction.user}")
    
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to modify this channel!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="vclimit", description="Set voice channel user limit")
@app_commands.describe(limit="User limit (0-99, 0 = unlimited)")
async def vclimit(interaction: discord.Interaction, limit: int):
    if not await has_permission(interaction, "junior_moderator"):
        await interaction.response.send_message("❌ You need Junior Moderator permissions to use this command!", ephemeral=True)
        return
    
    if not interaction.user.voice:
        await interaction.response.send_message("❌ You need to be in a voice channel to use this command!", ephemeral=True)
        return
    
    if limit < 0 or limit > 99:
        await interaction.response.send_message("❌ Limit must be between 0-99 (0 = unlimited)!", ephemeral=True)
        return
    
    channel = interaction.user.voice.channel
    
    try:
        await channel.edit(user_limit=limit)
        
        limit_text = "Unlimited" if limit == 0 else str(limit)
        embed = discord.Embed(
            title="🔢 Voice Channel Limit Set",
            description=f"**Channel:** {channel.mention}\n**Limit:** {limit_text} users\n**Moderator:** {interaction.user.mention}",
            color=0x3498db
        )
        await interaction.response.send_message(embed=embed)
        
        await log_action(interaction.guild.id, "moderation", f"🛡 [VC LIMIT] {channel.name} limit set to {limit_text} by {interaction.user}")
    
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to modify this channel!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)
