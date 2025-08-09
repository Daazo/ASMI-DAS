
import discord
from discord.ext import commands
from discord import app_commands
from main import bot, has_permission, get_server_data, update_server_data, log_action

@bot.tree.command(name="reactionrole", description="🎭 Setup reaction roles")
@app_commands.describe(
    message="Message to send",
    emoji="Emoji for reaction",
    role="Role to assign",
    channel="Channel to send message",
    verification="Remove role when user reacts (verification system)"
)
async def reaction_role_setup(
    interaction: discord.Interaction,
    message: str,
    emoji: str,
    role: discord.Role,
    channel: discord.TextChannel,
    verification: bool = False
):
    if not await has_permission(interaction, "main_moderator"):
        await interaction.response.send_message("❌ You need Main Moderator permissions to use this command!", ephemeral=True)
        return
    
    try:
        # Send the message
        embed = discord.Embed(
            title="🎭 Reaction Roles",
            description=message,
            color=0x9b59b6
        )
        embed.set_footer(text="React to get your role!")
        
        sent_message = await channel.send(embed=embed)
        
        # Add reaction
        await sent_message.add_reaction(emoji)
        
        # Store reaction role data
        server_data = await get_server_data(interaction.guild.id)
        reaction_roles = server_data.get('reaction_roles', {})
        
        reaction_roles[str(sent_message.id)] = {
            'emoji': emoji,
            'role_id': str(role.id),
            'channel_id': str(channel.id),
            'verification': verification
        }
        
        await update_server_data(interaction.guild.id, {'reaction_roles': reaction_roles})
        
        response_embed = discord.Embed(
            title="✅ Reaction Role Setup Complete",
            description=f"**Message:** {channel.mention}\n**Emoji:** {emoji}\n**Role:** {role.mention}\n**Mode:** {'Verification (removes role)' if verification else 'Normal (adds role)'}",
            color=0x43b581
        )
        response_embed.set_footer(text="ᴠᴀᴀᴢʜᴀ")
        await interaction.response.send_message(embed=response_embed)
        
        await log_action(interaction.guild.id, "setup", f"🎭 [REACTION ROLE] Setup by {interaction.user} - {emoji} → {role.name}")
    
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.event
async def on_raw_reaction_add(payload):
    """Handle reaction role assignment"""
    if payload.user_id == bot.user.id:
        return
    
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return
    
    server_data = await get_server_data(guild.id)
    reaction_roles = server_data.get('reaction_roles', {})
    
    message_id = str(payload.message_id)
    if message_id in reaction_roles:
        reaction_data = reaction_roles[message_id]
        
        if str(payload.emoji) == reaction_data['emoji']:
            role = guild.get_role(int(reaction_data['role_id']))
            member = guild.get_member(payload.user_id)
            is_verification = reaction_data.get('verification', False)
            
            if role and member:
                try:
                    if is_verification and role in member.roles:
                        # Verification mode: remove role when reacting
                        await member.remove_roles(role, reason="Verification reaction role removal")
                        await log_action(guild.id, "moderation", f"🎭 [VERIFICATION ROLE] {role.name} removed from {member}")
                    elif not is_verification and role not in member.roles:
                        # Normal mode: add role when reacting
                        await member.add_roles(role, reason="Reaction role assignment")
                        await log_action(guild.id, "moderation", f"🎭 [REACTION ROLE] {role.name} added to {member}")
                except discord.Forbidden:
                    print(f"Missing permissions to modify role {role.name} for {member}")
                except discord.HTTPException as e:
                    print(f"Failed to modify role: {e}")

@bot.event
async def on_raw_reaction_remove(payload):
    """Handle reaction role removal with verification"""
    if payload.user_id == bot.user.id:
        return
    
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return
    
    server_data = await get_server_data(guild.id)
    reaction_roles = server_data.get('reaction_roles', {})
    
    message_id = str(payload.message_id)
    if message_id in reaction_roles:
        reaction_data = reaction_roles[message_id]
        
        if str(payload.emoji) == reaction_data['emoji']:
            role = guild.get_role(int(reaction_data['role_id']))
            member = guild.get_member(payload.user_id)
            is_verification = reaction_data.get('verification', False)
            
            if role and member:
                try:
                    if is_verification and role not in member.roles:
                        # Verification mode: add role when removing reaction
                        await member.add_roles(role, reason="Verification reaction role restoration")
                        await log_action(guild.id, "moderation", f"🎭 [VERIFICATION ROLE] {role.name} restored to {member}")
                    elif not is_verification and role in member.roles:
                        # Normal mode: remove role when removing reaction
                        await member.remove_roles(role, reason="Reaction role removal")
                        await log_action(guild.id, "moderation", f"🎭 [REACTION ROLE] {role.name} removed from {member}")
                except discord.Forbidden:
                    print(f"Missing permissions to modify role {role.name} for {member}")
                except discord.HTTPException as e:
                    print(f"Failed to modify role: {e}")

# Remove duplicate event handlers - keeping only the first set
