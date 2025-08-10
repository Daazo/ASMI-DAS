
import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
from datetime import datetime, timedelta
from main import bot, has_permission, log_action, db

@bot.tree.command(name="giverole", description="🎭 Give a role to a user for a limited time")
@app_commands.describe(
    user="User to give role to",
    role="Role to assign",
    duration="Duration (e.g., 1d, 5h, 30m)"
)
async def give_timed_role(interaction: discord.Interaction, user: discord.Member, role: discord.Role, duration: str):
    if not await has_permission(interaction, "main_moderator"):
        await interaction.response.send_message("❌ You need Main Moderator permissions to use this command!", ephemeral=True)
        return
    
    # Parse duration
    import re
    time_regex = re.compile(r'(\d+)([smhd])')
    matches = time_regex.findall(duration.lower())
    
    if not matches:
        await interaction.response.send_message("❌ Invalid duration format! Use: 30s, 5m, 2h, 7d", ephemeral=True)
        return
    
    total_seconds = 0
    for amount, unit in matches:
        amount = int(amount)
        if unit == 's':
            total_seconds += amount
        elif unit == 'm':
            total_seconds += amount * 60
        elif unit == 'h':
            total_seconds += amount * 3600
        elif unit == 'd':
            total_seconds += amount * 86400
    
    if total_seconds > 86400 * 30:  # Max 30 days
        await interaction.response.send_message("❌ Maximum duration is 30 days!", ephemeral=True)
        return
    
    if total_seconds < 60:  # Min 1 minute
        await interaction.response.send_message("❌ Minimum duration is 1 minute!", ephemeral=True)
        return
    
    # Check if user already has the role
    if role in user.roles:
        await interaction.response.send_message(f"❌ {user.mention} already has the {role.mention} role!", ephemeral=True)
        return
    
    # Check role hierarchy
    if role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("❌ You cannot assign a role equal or higher than your own!", ephemeral=True)
        return
    
    if role >= interaction.guild.me.top_role:
        await interaction.response.send_message("❌ I cannot assign a role equal or higher than my own!", ephemeral=True)
        return
    
    # Add role
    try:
        await user.add_roles(role, reason=f"Timed role by {interaction.user} for {duration}")
        
        # Store in database for removal
        if db:
            expire_time = datetime.utcnow() + timedelta(seconds=total_seconds)
            await db.timed_roles.insert_one({
                'user_id': str(user.id),
                'guild_id': str(interaction.guild.id),
                'role_id': str(role.id),
                'expire_time': expire_time,
                'assigned_by': str(interaction.user.id)
            })
        
        # Format duration for display
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        
        duration_str = []
        if days > 0:
            duration_str.append(f"{days}d")
        if hours > 0:
            duration_str.append(f"{hours}h")
        if minutes > 0:
            duration_str.append(f"{minutes}m")
        
        embed = discord.Embed(
            title="🎭 Timed Role Assigned",
            description=f"**User:** {user.mention}\n**Role:** {role.mention}\n**Duration:** {' '.join(duration_str)}\n**Assigned by:** {interaction.user.mention}",
            color=0x43b581
        )
        embed.add_field(
            name="⏰ Expires",
            value=f"{discord.utils.format_dt(datetime.utcnow() + timedelta(seconds=total_seconds), 'F')}",
            inline=False
        )
        embed.set_footer(text="ᴠᴀᴀᴢʜᴀ")
        
        await interaction.response.send_message(embed=embed)
        
        # Schedule role removal
        bot.loop.create_task(remove_role_after_delay(user, role, total_seconds, interaction.guild))
        
        await log_action(interaction.guild.id, "moderation", f"🎭 [TIMED ROLE] {role.name} given to {user} by {interaction.user} for {duration}")
    
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to assign this role!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="removetimerole", description="⏰ Remove a timed role early")
@app_commands.describe(user="User to remove role from", role="Role to remove")
async def remove_timed_role(interaction: discord.Interaction, user: discord.Member, role: discord.Role):
    if not await has_permission(interaction, "main_moderator"):
        await interaction.response.send_message("❌ You need Main Moderator permissions to use this command!", ephemeral=True)
        return
    
    if role not in user.roles:
        await interaction.response.send_message(f"❌ {user.mention} doesn't have the {role.mention} role!", ephemeral=True)
        return
    
    # Remove from database
    if db:
        await db.timed_roles.delete_one({
            'user_id': str(user.id),
            'guild_id': str(interaction.guild.id),
            'role_id': str(role.id)
        })
    
    # Remove role
    try:
        await user.remove_roles(role, reason=f"Timed role removed early by {interaction.user}")
        
        embed = discord.Embed(
            title="⏰ Timed Role Removed",
            description=f"**Role:** {role.mention} removed from {user.mention}",
            color=0xf39c12
        )
        embed.set_footer(text="ᴠᴀᴀᴢʜᴀ")
        
        await interaction.response.send_message(embed=embed)
        
        await log_action(interaction.guild.id, "moderation", f"⏰ [TIMED ROLE] {role.name} removed early from {user} by {interaction.user}")
    
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to remove this role!", ephemeral=True)

async def remove_role_after_delay(user, role, delay_seconds, guild):
    """Remove role after specified delay"""
    await asyncio.sleep(delay_seconds)
    
    # Check if user still has the role and is in the guild
    member = guild.get_member(user.id)
    if member and role in member.roles:
        try:
            await member.remove_roles(role, reason="Timed role expired")
            
            # Remove from database
            if db:
                await db.timed_roles.delete_one({
                    'user_id': str(user.id),
                    'guild_id': str(guild.id),
                    'role_id': str(role.id)
                })
            
            await log_action(guild.id, "moderation", f"⏰ [TIMED ROLE] {role.name} expired and removed from {member}")
        except:
            pass

@tasks.loop(minutes=5)
async def check_expired_roles():
    """Check for expired timed roles every 5 minutes"""
    if not db:
        return
    
    now = datetime.utcnow()
    expired_roles = await db.timed_roles.find({'expire_time': {'$lte': now}}).to_list(length=None)
    
    for role_data in expired_roles:
        guild = bot.get_guild(int(role_data['guild_id']))
        if not guild:
            continue
            
        member = guild.get_member(int(role_data['user_id']))
        if not member:
            continue
            
        role = guild.get_role(int(role_data['role_id']))
        if not role:
            continue
        
        if role in member.roles:
            try:
                await member.remove_roles(role, reason="Timed role expired")
                await log_action(guild.id, "moderation", f"⏰ [TIMED ROLE] {role.name} expired and removed from {member}")
            except:
                pass
        
        # Remove from database
        await db.timed_roles.delete_one({'_id': role_data['_id']})

@check_expired_roles.before_loop
async def before_check_expired_roles():
    await bot.wait_until_ready()

# Start the task
check_expired_roles.start()
