
import discord
from discord.ext import commands
from discord import app_commands
from main import bot, has_permission, get_server_data, update_server_data, log_action

@bot.tree.command(name="autoremoverole", description="🔄 Setup automatic role removal when users get specific roles")
@app_commands.describe(
    remove_role="Role to automatically remove",
    reason_role="When user gets this role, the remove_role will be taken away",
    action="Add or remove auto-remove rule"
)
@app_commands.choices(action=[
    app_commands.Choice(name="add", value="add"),
    app_commands.Choice(name="remove", value="remove"),
    app_commands.Choice(name="list", value="list")
])
async def auto_remove_role_setup(
    interaction: discord.Interaction,
    action: str,
    remove_role: discord.Role = None,
    reason_role: discord.Role = None
):
    if not await has_permission(interaction, "main_moderator"):
        await interaction.response.send_message("❌ You need Main Moderator permissions to use this command!", ephemeral=True)
        return
    
    server_data = await get_server_data(interaction.guild.id)
    auto_remove_rules = server_data.get('auto_remove_rules', {})
    
    if action == "add":
        if not remove_role or not reason_role:
            await interaction.response.send_message("❌ Please specify both remove_role and reason_role!", ephemeral=True)
            return
        
        if remove_role.id == reason_role.id:
            await interaction.response.send_message("❌ Remove role and reason role cannot be the same!", ephemeral=True)
            return
        
        # Check if bot can manage these roles
        if remove_role >= interaction.guild.me.top_role or reason_role >= interaction.guild.me.top_role:
            await interaction.response.send_message("❌ I cannot manage these roles! Please make sure my role is higher than both roles.", ephemeral=True)
            return
        
        # Add the rule
        auto_remove_rules[str(reason_role.id)] = str(remove_role.id)
        await update_server_data(interaction.guild.id, {'auto_remove_rules': auto_remove_rules})
        
        embed = discord.Embed(
            title="✅ Auto-Remove Rule Added",
            description=f"**When user gets:** {reason_role.mention}\n**Bot will remove:** {remove_role.mention}\n**Set by:** {interaction.user.mention}",
            color=0x43b581
        )
        embed.set_footer(text="🔄 Auto-remove system active • ᴠᴀᴀᴢʜᴀ")
        await interaction.response.send_message(embed=embed)
        
        await log_action(interaction.guild.id, "setup", f"🔄 [AUTO-REMOVE] Rule added: {reason_role.name} → remove {remove_role.name} by {interaction.user}")
    
    elif action == "remove":
        if not reason_role:
            await interaction.response.send_message("❌ Please specify the reason_role to remove the rule for!", ephemeral=True)
            return
        
        if str(reason_role.id) not in auto_remove_rules:
            await interaction.response.send_message(f"❌ No auto-remove rule found for {reason_role.mention}!", ephemeral=True)
            return
        
        # Get the remove role for display
        remove_role_id = auto_remove_rules[str(reason_role.id)]
        remove_role_obj = interaction.guild.get_role(int(remove_role_id))
        remove_role_name = remove_role_obj.mention if remove_role_obj else "Unknown Role"
        
        # Remove the rule
        del auto_remove_rules[str(reason_role.id)]
        await update_server_data(interaction.guild.id, {'auto_remove_rules': auto_remove_rules})
        
        embed = discord.Embed(
            title="✅ Auto-Remove Rule Removed",
            description=f"**Removed rule:** {reason_role.mention} → {remove_role_name}\n**Removed by:** {interaction.user.mention}",
            color=0xf39c12
        )
        embed.set_footer(text="🔄 Auto-remove rule deleted • ᴠᴀᴀᴢʜᴀ")
        await interaction.response.send_message(embed=embed)
        
        await log_action(interaction.guild.id, "setup", f"🔄 [AUTO-REMOVE] Rule removed: {reason_role.name} by {interaction.user}")
    
    elif action == "list":
        if not auto_remove_rules:
            embed = discord.Embed(
                title="📋 Auto-Remove Rules",
                description="No auto-remove rules are currently set in this server.\n\nUse `/autoremoverole add` to create rules!",
                color=0x95a5a6
            )
            embed.set_footer(text="🔄 Auto-remove system • ᴠᴀᴀᴢʜᴀ")
            await interaction.response.send_message(embed=embed)
            return
        
        embed = discord.Embed(
            title="📋 **Active Auto-Remove Rules**",
            description=f"*Found {len(auto_remove_rules)} active rule(s)*\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=0x9b59b6
        )
        
        count = 0
        for reason_role_id, remove_role_id in list(auto_remove_rules.items())[:10]:  # Show max 10
            count += 1
            reason_role_obj = interaction.guild.get_role(int(reason_role_id))
            remove_role_obj = interaction.guild.get_role(int(remove_role_id))
            
            reason_role_name = reason_role_obj.mention if reason_role_obj else "Unknown Role"
            remove_role_name = remove_role_obj.mention if remove_role_obj else "Unknown Role"
            
            embed.add_field(
                name=f"#{count} Auto-Remove Rule",
                value=f"**When user gets:** {reason_role_name}\n**Bot removes:** {remove_role_name}",
                inline=False
            )
        
        if len(auto_remove_rules) > 10:
            embed.add_field(
                name="📊 Additional Rules",
                value=f"*{len(auto_remove_rules) - 10} more rules not shown*",
                inline=False
            )
        
        embed.set_footer(text="🔄 Use /autoremoverole remove to delete rules • ᴠᴀᴀᴢʜᴀ")
        await interaction.response.send_message(embed=embed)

@bot.event
async def on_member_update(before, after):
    """Handle auto-remove role functionality when member roles change"""
    if before.roles == after.roles:
        return  # No role changes
    
    # Get added roles
    added_roles = set(after.roles) - set(before.roles)
    if not added_roles:
        return  # No roles were added
    
    # Get server auto-remove rules
    server_data = await get_server_data(after.guild.id)
    auto_remove_rules = server_data.get('auto_remove_rules', {})
    
    if not auto_remove_rules:
        return  # No auto-remove rules set
    
    # Check each added role against auto-remove rules
    for added_role in added_roles:
        if str(added_role.id) in auto_remove_rules:
            remove_role_id = auto_remove_rules[str(added_role.id)]
            remove_role = after.guild.get_role(int(remove_role_id))
            
            if remove_role and remove_role in after.roles:
                try:
                    await after.remove_roles(remove_role, reason=f"Auto-remove: User got {added_role.name}")
                    await log_action(after.guild.id, "moderation", f"🔄 [AUTO-REMOVE] {remove_role.name} removed from {after} (got {added_role.name})")
                    
                    # Send notification to user
                    try:
                        embed = discord.Embed(
                            title="🔄 **Role Auto-Removed**",
                            description=f"Your **{remove_role.name}** role was automatically removed in **{after.guild.name}** because you received the **{added_role.name}** role.",
                            color=0xf39c12
                        )
                        embed.set_footer(text="🔄 Auto-remove system • ᴠᴀᴀᴢʜᴀ")
                        await after.send(embed=embed)
                    except:
                        pass  # User has DMs disabled
                        
                except discord.Forbidden:
                    await log_action(after.guild.id, "moderation", f"❌ [AUTO-REMOVE] Failed to remove {remove_role.name} from {after} - Missing permissions")
                except Exception as e:
                    await log_action(after.guild.id, "moderation", f"❌ [AUTO-REMOVE] Error removing {remove_role.name} from {after}: {str(e)}")
