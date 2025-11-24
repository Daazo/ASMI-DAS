
import discord
from discord.ext import commands, tasks
from discord import app_commands
from main import bot, db
from brand_config import create_permission_denied_embed, create_owner_only_embed,  BOT_FOOTER, BrandColors, create_success_embed, create_error_embed, create_info_embed, create_command_embed, create_warning_embed
from main import has_permission, log_action
from datetime import datetime, timedelta
import asyncio

@bot.tree.command(name="mute", description="🔇 Mute user in voice channel")
@app_commands.describe(user="User to mute")
async def mute(interaction: discord.Interaction, user: discord.Member):
    if not await has_permission(interaction, "junior_moderator"):
        await interaction.response.send_message(embed=create_permission_denied_embed("Junior Moderator"), ephemeral=True)
        return

    if not user.voice:
        await interaction.response.send_message("❌ User is not in a voice channel!", ephemeral=True)
        return

    try:
        await user.edit(mute=True)

        embed = discord.Embed(
            title="🔇 User Muted",
            description=f"**User:** {user.mention}\n**Moderator:** {interaction.user.mention}",
            color=BrandColors.WARNING
        )
        await interaction.response.send_message(embed=embed)
        
        await log_action(interaction.guild.id, "moderation", f"🔇 [MUTE] {user} muted by {interaction.user}")

        # Log to global per-server channel
        try:
            from advanced_logging import send_global_log
            await send_global_log("moderation", f"**🔇 Mute**\n**User:** {user}\n**Moderator:** {interaction.user}", interaction.guild)
        except:
            pass

    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to mute this user!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="unmute", description="🔊 Unmute user in voice channel")
@app_commands.describe(user="User to unmute")
async def unmute(interaction: discord.Interaction, user: discord.Member):
    if not await has_permission(interaction, "junior_moderator"):
        await interaction.response.send_message(embed=create_permission_denied_embed("Junior Moderator"), ephemeral=True)
        return

    if not user.voice:
        await interaction.response.send_message("❌ User is not in a voice channel!", ephemeral=True)
        return

    try:
        await user.edit(mute=False)

        embed = discord.Embed(
            title="🔊 User Unmuted",
            description=f"**User:** {user.mention}\n**Moderator:** {interaction.user.mention}",
            color=BrandColors.SUCCESS
        )
        await interaction.response.send_message(embed=embed)
        
        await log_action(interaction.guild.id, "moderation", f"🔊 [UNMUTE] {user} unmuted by {interaction.user}")

        # Log to global per-server channel
        try:
            from advanced_logging import send_global_log
            await send_global_log("moderation", f"**🔊 Unmute**\n**User:** {user}\n**Moderator:** {interaction.user}", interaction.guild)
        except:
            pass

    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to unmute this user!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="movevc", description="Move user to different voice channel")
@app_commands.describe(user="User to move", channel="Voice channel to move to")
async def movevc(interaction: discord.Interaction, user: discord.Member, channel: discord.VoiceChannel):
    if not await has_permission(interaction, "junior_moderator"):
        await interaction.response.send_message(embed=create_permission_denied_embed("Junior Moderator"), ephemeral=True)
        return

    if not user.voice:
        await interaction.response.send_message("❌ User is not in a voice channel!", ephemeral=True)
        return

    try:
        await user.move_to(channel)

        embed = discord.Embed(
            title="🔀 User Moved",
            description=f"**User:** {user.mention}\n**Moved to:** {channel.mention}\n**Moderator:** {interaction.user.mention}",
            color=BrandColors.SUCCESS
        )
        await interaction.response.send_message(embed=embed)
        
        await log_action(interaction.guild.id, "moderation", f"🛡 [MOVE VC] {user} moved to {channel.name} by {interaction.user}")

        # Log to global per-server channel
        try:
            from advanced_logging import send_global_log
            await send_global_log("moderation", f"**🔀 Move VC**\n**User:** {user}\n**Moved to:** {channel.mention}\n**Moderator:** {interaction.user}", interaction.guild)
        except:
            pass

    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to move this user!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="vckick", description="Kick user from voice channel")
@app_commands.describe(user="User to kick from voice")
async def vckick(interaction: discord.Interaction, user: discord.Member):
    if not await has_permission(interaction, "junior_moderator"):
        await interaction.response.send_message(embed=create_permission_denied_embed("Junior Moderator"), ephemeral=True)
        return

    if not user.voice:
        await interaction.response.send_message("❌ User is not in a voice channel!", ephemeral=True)
        return

    try:
        await user.move_to(None)

        embed = discord.Embed(
            title="👢 User Kicked from VC",
            description=f"**User:** {user.mention}\n**Moderator:** {interaction.user.mention}",
            color=BrandColors.WARNING
        )
        await interaction.response.send_message(embed=embed)
        
        await log_action(interaction.guild.id, "moderation", f"🛡 [VC KICK] {user} kicked from voice by {interaction.user}")

        # Log to global per-server channel
        try:
            from advanced_logging import send_global_log
            await send_global_log("moderation", f"**👢 VC Kick**\n**User:** {user}\n**Moderator:** {interaction.user}", interaction.guild)
        except:
            pass

    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to disconnect this user!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="vclock", description="Lock current voice channel")
async def vclock(interaction: discord.Interaction):
    if not await has_permission(interaction, "junior_moderator"):
        await interaction.response.send_message(embed=create_permission_denied_embed("Junior Moderator"), ephemeral=True)
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
            color=BrandColors.DANGER
        )
        await interaction.response.send_message(embed=embed)
        
        await log_action(interaction.guild.id, "moderation", f"🛡 [VC LOCK] {channel.name} locked by {interaction.user}")

        # Log to global per-server channel
        try:
            from advanced_logging import send_global_log
            await send_global_log("moderation", f"**🔒 VC Lock**\n**Channel:** {channel.mention}\n**Moderator:** {interaction.user}", interaction.guild)
        except:
            pass

    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to modify this channel!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="vcunlock", description="Unlock current voice channel")
async def vcunlock(interaction: discord.Interaction):
    if not await has_permission(interaction, "junior_moderator"):
        await interaction.response.send_message(embed=create_permission_denied_embed("Junior Moderator"), ephemeral=True)
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
            color=BrandColors.SUCCESS
        )
        await interaction.response.send_message(embed=embed)
        
        await log_action(interaction.guild.id, "moderation", f"🛡 [VC UNLOCK] {channel.name} unlocked by {interaction.user}")

        # Log to global per-server channel
        try:
            from advanced_logging import send_global_log
            await send_global_log("moderation", f"**🔓 VC Unlock**\n**Channel:** {channel.mention}\n**Moderator:** {interaction.user}", interaction.guild)
        except:
            pass

    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to modify this channel!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="vclimit", description="Set voice channel user limit")
@app_commands.describe(limit="User limit (0-99, 0 = unlimited)")
async def vclimit(interaction: discord.Interaction, limit: int):
    if not await has_permission(interaction, "junior_moderator"):
        await interaction.response.send_message(embed=create_permission_denied_embed("Junior Moderator"), ephemeral=True)
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
            color=BrandColors.INFO
        )
        await interaction.response.send_message(embed=embed)
        
        await log_action(interaction.guild.id, "moderation", f"🛡 [VC LIMIT] {channel.name} limit set to {limit_text} by {interaction.user}")

    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to modify this channel!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

# ═══════════════════════════════════════════════════════════════════════════
# CUSTOM VOICE CHANNEL SYSTEM - DYNAMIC VC ON DEMAND
# ═══════════════════════════════════════════════════════════════════════════

class CustomVCNameModal(discord.ui.Modal):
    def __init__(self, hub_channel, category, guild):
        super().__init__(title="🔊 Create Custom Voice Channel")
        self.hub_channel = hub_channel
        self.category = category
        self.guild = guild
        
    vc_name = discord.ui.TextInput(
        label="Channel Name",
        placeholder="Enter your custom voice channel name (max 100 chars)",
        required=True,
        max_length=100,
        min_length=1
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        try:
            custom_name = self.vc_name.value.strip()
            new_vc = await self.category.create_voice_channel(
                name=custom_name,
                reason=f"Custom VC created by {interaction.user}"
            )
            
            await interaction.user.move_to(new_vc)
            
            if db:
                await db.custom_vcs.insert_one({
                    'guild_id': str(self.guild.id),
                    'channel_id': str(new_vc.id),
                    'creator_id': str(interaction.user.id),
                    'created_at': datetime.utcnow(),
                    'last_activity': datetime.utcnow()
                })
            
            embed = discord.Embed(
                title="✅ **Custom VC Created**",
                description=f"**🔊 Channel:** {new_vc.mention}\n**Created by:** {interaction.user.mention}\n**Name:** {custom_name}",
                color=BrandColors.SUCCESS
            )
            embed.set_footer(text=f"{BOT_FOOTER} • Auto-deletes after 5 minutes of inactivity")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            await log_action(self.guild.id, "custom_vc", f"🔊 [CUSTOM VC] Created by {interaction.user}: {custom_name}")
            
            try:
                from advanced_logging import send_global_log
                await send_global_log("custom_vc", f"**🔊 Custom VC Created**\n**Creator:** {interaction.user}\n**Channel:** {new_vc.mention}\n**Name:** {custom_name}", self.guild)
            except:
                pass
        
        except Exception as e:
            await interaction.followup.send(embed=create_error_embed(f"Failed to create VC: {str(e)}"), ephemeral=True)

@bot.tree.command(name="custom-vc", description="🔊 Setup dynamic custom voice channel system")
@app_commands.describe(category="Category to create custom VCs in")
async def custom_vc_setup(interaction: discord.Interaction, category: discord.CategoryChannel):
    if not await has_permission(interaction, "main_moderator"):
        await interaction.response.send_message(embed=create_permission_denied_embed("Main Moderator"), ephemeral=True)
        return
    
    try:
        hub_channel = await category.create_voice_channel(
            name="🔊 CUSTOM VC",
            reason=f"Custom VC hub created by {interaction.user}"
        )
        
        if db:
            await db.custom_vc_hubs.update_one(
                {'guild_id': str(interaction.guild.id)},
                {'$set': {
                    'hub_channel_id': str(hub_channel.id),
                    'category_id': str(category.id),
                    'created_by': str(interaction.user.id),
                    'created_at': datetime.utcnow()
                }},
                upsert=True
            )
        
        embed = discord.Embed(
            title="⚡ **Custom VC System Setup Complete**",
            description=f"**🔊 Hub Channel:** {hub_channel.mention}\n**📁 Category:** {category.mention}\n**Status:** Active & Ready",
            color=BrandColors.PRIMARY
        )
        embed.add_field(
            name="🎯 How It Works",
            value="✓ Users join 🔊 CUSTOM VC\n✓ Use `/create-custom-vc` to name their VC\n✓ Custom channel auto-created\n✓ Auto-deletes after 5 min inactivity",
            inline=False
        )
        embed.set_footer(text=BOT_FOOTER)
        await interaction.response.send_message(embed=embed)
        
        await log_action(interaction.guild.id, "custom_vc", f"⚡ [CUSTOM VC SETUP] System setup by {interaction.user}")
        
    except Exception as e:
        await interaction.response.send_message(embed=create_error_embed(f"Setup failed: {str(e)}"), ephemeral=True)

@bot.tree.command(name="create-custom-vc", description="🔊 Create your own temporary voice channel")
@app_commands.describe(name="Name for your custom voice channel")
async def create_custom_vc(interaction: discord.Interaction, name: str):
    try:
        if not interaction.user.voice:
            await interaction.response.send_message(embed=create_error_embed("You must be in the 🔊 CUSTOM VC hub first!"), ephemeral=True)
            return
        
        if db:
            hub_data = await db.custom_vc_hubs.find_one({'guild_id': str(interaction.guild.id)})
            if not hub_data:
                await interaction.response.send_message(embed=create_error_embed("Custom VC system not setup! Admin must run `/custom-vc`"), ephemeral=True)
                return
            
            hub_id = int(hub_data['hub_channel_id'])
            hub_channel = interaction.guild.get_channel(hub_id)
            
            if hub_channel and interaction.user.voice.channel.id == hub_id:
                category = hub_channel.category
                
                custom_name = name.strip()[:100]
                new_vc = await category.create_voice_channel(
                    name=custom_name,
                    reason=f"Custom VC by {interaction.user}"
                )
                
                await interaction.user.move_to(new_vc)
                
                await db.custom_vcs.insert_one({
                    'guild_id': str(interaction.guild.id),
                    'channel_id': str(new_vc.id),
                    'creator_id': str(interaction.user.id),
                    'created_at': datetime.utcnow(),
                    'last_activity': datetime.utcnow()
                })
                
                embed = discord.Embed(
                    title="✅ **Custom VC Created**",
                    description=f"**🔊 Channel:** {new_vc.mention}\n**Name:** {custom_name}",
                    color=BrandColors.SUCCESS
                )
                embed.set_footer(text=f"{BOT_FOOTER} • Auto-deletes after 5 minutes of inactivity")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
                await log_action(interaction.guild.id, "custom_vc", f"🔊 [CUSTOM VC] {interaction.user} created: {custom_name}")
                
                try:
                    from advanced_logging import send_global_log
                    await send_global_log("custom_vc", f"**🔊 Custom VC Created**\n**Creator:** {interaction.user}\n**Channel:** {new_vc.mention}\n**Name:** {custom_name}", interaction.guild)
                except:
                    pass
            else:
                await interaction.response.send_message(embed=create_error_embed("You must be in the 🔊 CUSTOM VC hub!"), ephemeral=True)
    
    except Exception as e:
        await interaction.response.send_message(embed=create_error_embed(f"Error: {str(e)}"), ephemeral=True)

@bot.event
async def on_voice_state_update_custom(member, before, after):
    """Update activity timestamp for custom VCs"""
    if after.channel and db:
        try:
            custom_vc = await db.custom_vcs.find_one({'channel_id': str(after.channel.id)})
            if custom_vc:
                await db.custom_vcs.update_one(
                    {'channel_id': str(after.channel.id)},
                    {'$set': {'last_activity': datetime.utcnow()}}
                )
        except:
            pass

@tasks.loop(minutes=1)
async def cleanup_empty_custom_vcs():
    """Auto-delete empty custom VCs after 5 minutes"""
    if not db:
        return
    
    try:
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)
        expired_vcs = await db.custom_vcs.find({'last_activity': {'$lt': cutoff_time}}).to_list(length=None)
        
        for vc_data in expired_vcs:
            try:
                guild_id = int(vc_data['guild_id'])
                channel_id = int(vc_data['channel_id'])
                
                guild = bot.get_guild(guild_id)
                if guild:
                    channel = guild.get_channel(channel_id)
                    if channel and len(channel.members) == 0:
                        vc_name = channel.name
                        await channel.delete(reason="Custom VC auto-cleanup - inactivity")
                        await log_action(guild_id, "custom_vc", f"🗑️ [CUSTOM VC DELETED] {vc_name} - inactivity")
                        
                        try:
                            from advanced_logging import send_global_log
                            await send_global_log("custom_vc", f"**🗑️ Custom VC Deleted**\n**Channel:** {vc_name}\n**Reason:** Inactivity (5 mins)", guild)
                        except:
                            pass
                
                await db.custom_vcs.delete_one({'_id': vc_data['_id']})
            except Exception as e:
                print(f"Error cleaning up custom VC: {e}")
    
    except Exception as e:
        print(f"Error in cleanup_empty_custom_vcs: {e}")

# Start cleanup task
if not cleanup_empty_custom_vcs.is_running():
    cleanup_empty_custom_vcs.start()
    print("✅ Custom VC cleanup task started")
