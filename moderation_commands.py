
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from main import bot, has_permission, log_action

@bot.tree.command(name="kick", description="Kick a user from the server")
@app_commands.describe(user="User to kick", reason="Reason for kick")
async def kick(interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
    if not await has_permission(interaction, "main_moderator"):
        await interaction.response.send_message("❌ You need Main Moderator permissions to use this command!", ephemeral=True)
        return
    
    if user.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("❌ You cannot kick someone with equal or higher role!", ephemeral=True)
        return
    
    try:
        await user.kick(reason=reason)
        
        embed = discord.Embed(
            title="👢 User Kicked",
            description=f"**User:** {user.mention}\n**Reason:** {reason}\n**Moderator:** {interaction.user.mention}",
            color=0xf39c12
        )
        await interaction.response.send_message(embed=embed)
        
        await log_action(interaction.guild.id, "moderation", f"🛡 [KICK] {user} kicked by {interaction.user} - Reason: {reason}")
        
        # Try to DM user
        try:
            dm_embed = discord.Embed(
                title=f"You were kicked from {interaction.guild.name}",
                description=f"**Reason:** {reason}\n**Moderator:** {interaction.user.display_name}",
                color=0xf39c12
            )
            await user.send(embed=dm_embed)
        except:
            pass
    
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to kick this user!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="ban", description="Ban a user from the server")
@app_commands.describe(user="User to ban", reason="Reason for ban")
async def ban(interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
    if not await has_permission(interaction, "main_moderator"):
        await interaction.response.send_message("❌ You need Main Moderator permissions to use this command!", ephemeral=True)
        return
    
    if user.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("❌ You cannot ban someone with equal or higher role!", ephemeral=True)
        return
    
    try:
        # Try to DM user before ban
        try:
            dm_embed = discord.Embed(
                title=f"You were banned from {interaction.guild.name}",
                description=f"**Reason:** {reason}\n**Moderator:** {interaction.user.display_name}",
                color=0xe74c3c
            )
            await user.send(embed=dm_embed)
        except:
            pass
        
        await user.ban(reason=reason)
        
        embed = discord.Embed(
            title="🔨 User Banned",
            description=f"**User:** {user.mention}\n**Reason:** {reason}\n**Moderator:** {interaction.user.mention}",
            color=0xe74c3c
        )
        await interaction.response.send_message(embed=embed)
        
        await log_action(interaction.guild.id, "moderation", f"🛡 [BAN] {user} banned by {interaction.user} - Reason: {reason}")
    
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to ban this user!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="nuke", description="Delete all messages in current channel")
async def nuke(interaction: discord.Interaction):
    if not await has_permission(interaction, "main_moderator"):
        await interaction.response.send_message("❌ You need Main Moderator permissions to use this command!", ephemeral=True)
        return
    
    # Confirmation view
    class NukeConfirmView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=30)
        
        @discord.ui.button(label="✅ Confirm Nuke", style=discord.ButtonStyle.danger)
        async def confirm(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if button_interaction.user != interaction.user:
                await button_interaction.response.send_message("❌ Only the command user can confirm!", ephemeral=True)
                return
            
            channel = interaction.channel
            channel_name = channel.name
            
            try:
                # Clone channel
                new_channel = await channel.clone(reason=f"Nuked by {interaction.user}")
                await channel.delete(reason=f"Nuked by {interaction.user}")
                
                embed = discord.Embed(
                    title="💥 Channel Nuked",
                    description=f"**Channel:** #{channel_name}\n**Moderator:** {interaction.user.mention}\n\nAll messages have been deleted!",
                    color=0xe74c3c
                )
                await new_channel.send(embed=embed)
                
                await log_action(interaction.guild.id, "moderation", f"🛡 [NUKE] #{channel_name} nuked by {interaction.user}")
            
            except discord.Forbidden:
                await button_interaction.response.send_message("❌ I don't have permission to delete/create channels!", ephemeral=True)
            except Exception as e:
                await button_interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)
        
        @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
        async def cancel(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if button_interaction.user != interaction.user:
                await button_interaction.response.send_message("❌ Only the command user can cancel!", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="❌ Nuke Cancelled",
                description="Channel nuke has been cancelled.",
                color=0x43b581
            )
            await button_interaction.response.edit_message(embed=embed, view=None)
    
    embed = discord.Embed(
        title="⚠️ DANGER: Nuke Channel",
        description=f"**This will DELETE ALL messages in {interaction.channel.mention}!**\n\nThis action is **IRREVERSIBLE**!\nAre you sure you want to proceed?",
        color=0xe74c3c
    )
    
    view = NukeConfirmView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="mute", description="Mute a user in voice channel")
@app_commands.describe(user="User to mute")
async def mute(interaction: discord.Interaction, user: discord.Member):
    if not await has_permission(interaction, "junior_moderator"):
        await interaction.response.send_message("❌ You need Junior Moderator permissions to use this command!", ephemeral=True)
        return
    
    if not user.voice:
        await interaction.response.send_message("❌ User is not in a voice channel!", ephemeral=True)
        return
    
    try:
        await user.edit(mute=True)
        
        embed = discord.Embed(
            title="🔇 User Muted",
            description=f"**User:** {user.mention}\n**Moderator:** {interaction.user.mention}",
            color=0xf39c12
        )
        await interaction.response.send_message(embed=embed)
        
        await log_action(interaction.guild.id, "moderation", f"🛡 [MUTE] {user} muted by {interaction.user}")
    
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to mute this user!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="unmute", description="Unmute a user in voice channel")
@app_commands.describe(user="User to unmute")
async def unmute(interaction: discord.Interaction, user: discord.Member):
    if not await has_permission(interaction, "junior_moderator"):
        await interaction.response.send_message("❌ You need Junior Moderator permissions to use this command!", ephemeral=True)
        return
    
    if not user.voice:
        await interaction.response.send_message("❌ User is not in a voice channel!", ephemeral=True)
        return
    
    try:
        await user.edit(mute=False)
        
        embed = discord.Embed(
            title="🔊 User Unmuted",
            description=f"**User:** {user.mention}\n**Moderator:** {interaction.user.mention}",
            color=0x43b581
        )
        await interaction.response.send_message(embed=embed)
        
        await log_action(interaction.guild.id, "moderation", f"🛡 [UNMUTE] {user} unmuted by {interaction.user}")
    
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to unmute this user!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)
