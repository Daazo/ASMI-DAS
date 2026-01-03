
import discord
from discord.ext import commands
from discord import app_commands
from main import bot
from brand_config import create_permission_denied_embed, create_owner_only_embed,  BOT_FOOTER, BrandColors, create_success_embed, create_error_embed, create_info_embed, create_command_embed, create_warning_embed
from main import has_permission, get_server_data, update_server_data, log_action


class ButtonRole(discord.ui.Button):
    def __init__(self, label, role_id, emoji=None, auto_remove_role_id=None):
        super().__init__(style=discord.ButtonStyle.secondary, label=label, emoji=emoji, custom_id=f"btn_role_{role_id}")
        self.role_id = int(role_id)
        self.auto_remove_role_id = int(auto_remove_role_id) if auto_remove_role_id else None

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        role = guild.get_role(self.role_id)
        if not role:
            return await interaction.response.send_message("❌ This role no longer exists.", ephemeral=True)

        member = interaction.user
        try:
            if role in member.roles:
                await member.remove_roles(role, reason="Button role removal")
                await interaction.response.send_message(f"✅ Removed role: **{role.name}**", ephemeral=True)
                await log_action(guild.id, "reaction_role", f"🎭 [BUTTON ROLE] {role.name} removed from {member}")
            else:
                # Handle auto-remove role functionality
                if self.auto_remove_role_id:
                    auto_remove_role = guild.get_role(self.auto_remove_role_id)
                    if auto_remove_role and auto_remove_role in member.roles:
                        await member.remove_roles(auto_remove_role, reason="Auto-remove role on button role assignment")
                        await log_action(guild.id, "reaction_role", f"🔄 [AUTO-REMOVE] {auto_remove_role.name} removed from {member}")

                await member.add_roles(role, reason="Button role assignment")
                await interaction.response.send_message(f"✅ Added role: **{role.name}**", ephemeral=True)
                await log_action(guild.id, "reaction_role", f"🎭 [BUTTON ROLE] {role.name} added to {member}")
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to manage this role.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class ButtonRoleView(discord.ui.View):
    def __init__(self, pairs, auto_remove_role_id=None):
        super().__init__(timeout=None)
        for emoji, role_id, role_name in pairs:
            self.add_item(ButtonRole(label=role_name, role_id=role_id, emoji=emoji, auto_remove_role_id=auto_remove_role_id))

@bot.tree.command(name="reactionrole", description="🎭 Setup button-based roles with multiple role pairs")
@app_commands.describe(
    channel="Channel to send the reaction role message",
    title="Title for the reaction role embed",
    description="Description explaining the roles",
    auto_remove_role="Role to automatically remove when users get any reaction role"
)
async def reaction_role_setup(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    title: str,
    description: str,
    auto_remove_role: discord.Role = None
):
    if not await has_permission(interaction, "main_moderator"):
        await interaction.response.send_message(embed=create_permission_denied_embed("Main Moderator"), ephemeral=True)
        return

    class ButtonRoleModal(discord.ui.Modal):
        def __init__(self, channel, title, description, auto_remove_role):
            super().__init__(title="🎭 Button Role Setup")
            self.channel = channel
            self.embed_title = title
            self.embed_description = description
            self.auto_remove_role = auto_remove_role

        emoji_role_pairs = discord.ui.TextInput(
            label="Emoji:Role Pairs (one per line)",
            placeholder="🎯:@Role1\n⭐:@Role2\n🎮:@Role3\n(Max 10 pairs)",
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=True
        )

        async def on_submit(self, modal_interaction: discord.Interaction):
            await modal_interaction.response.defer()
            try:
                pairs = []
                lines = self.emoji_role_pairs.value.strip().split('\n')
                for line in lines:
                    if ':' not in line: continue
                    emoji, role_part = [x.strip() for x in line.split(':', 1)]
                    role_id = None
                    if role_part.startswith('<@&') and role_part.endswith('>'):
                        role_id = role_part[3:-1]
                    elif role_part.startswith('@'):
                        rn = role_part[1:]
                        for r in modal_interaction.guild.roles:
                            if r.name.lower() == rn.lower():
                                role_id = str(r.id)
                                break
                    if role_id:
                        role = modal_interaction.guild.get_role(int(role_id))
                        if role: pairs.append((emoji, str(role.id), role.name))

                if not pairs:
                    return await modal_interaction.followup.send("❌ No valid pairs found!", ephemeral=True)

                embed = discord.Embed(title=f"🎭 {self.embed_title}", description=self.embed_description, color=BrandColors.PRIMARY)
                embed.set_footer(text=f"Click buttons below to get your roles! • {BOT_FOOTER}")
                
                view = ButtonRoleView(pairs, str(self.auto_remove_role.id) if self.auto_remove_role else None)
                sent_message = await self.channel.send(embed=embed, view=view)

                server_data = await get_server_data(modal_interaction.guild.id)
                button_roles = server_data.get('button_roles', {})
                button_roles[str(sent_message.id)] = {
                    'pairs': pairs,
                    'auto_remove_role_id': str(self.auto_remove_role.id) if self.auto_remove_role else None
                }
                await update_server_data(modal_interaction.guild.id, {'button_roles': button_roles})

                await modal_interaction.followup.send(embed=create_success_embed("Setup Complete", f"Button roles sent to {self.channel.mention}"))
                await log_action(modal_interaction.guild.id, "reaction_role", f"🎭 [BUTTON ROLE] Setup by {modal_interaction.user}")
            except Exception as e:
                await modal_interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

    await interaction.response.send_modal(ButtonRoleModal(channel, title, description, auto_remove_role))

@bot.tree.command(name="quickreactionrole", description="🎭 Quick setup for single button role")
async def quick_reaction_role_setup(interaction: discord.Interaction, message: str, emoji: str, role: discord.Role, channel: discord.TextChannel, auto_remove_role: discord.Role = None):
    if not await has_permission(interaction, "main_moderator"):
        return await interaction.response.send_message(embed=create_permission_denied_embed("Main Moderator"), ephemeral=True)

    embed = discord.Embed(title="🎭 Get Your Role", description=message, color=BrandColors.PRIMARY)
    embed.set_footer(text=BOT_FOOTER)
    pairs = [(emoji, str(role.id), role.name)]
    view = ButtonRoleView(pairs, str(auto_remove_role.id) if auto_remove_role else None)
    sent_message = await channel.send(embed=embed, view=view)

    server_data = await get_server_data(interaction.guild.id)
    button_roles = server_data.get('button_roles', {})
    button_roles[str(sent_message.id)] = {'pairs': pairs, 'auto_remove_role_id': str(auto_remove_role.id) if auto_remove_role else None}
    await update_server_data(interaction.guild.id, {'button_roles': button_roles})

    await interaction.response.send_message(embed=create_success_embed("Quick Setup Complete", f"Button role sent to {channel.mention}"))
    await log_action(interaction.guild.id, "reaction_role", f"🎭 [QUICK BUTTON ROLE] {role.name} in {channel.name}")

@bot.event
async def on_raw_reaction_add(payload):
    """Handle reaction role assignment with multiple emoji support"""
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
        member = guild.get_member(payload.user_id)

        if not member:
            return

        # Check for multiple emoji/role pairs
        pairs = reaction_data.get('pairs', [])
        auto_remove_role_id = reaction_data.get('auto_remove_role_id')

        for emoji, role_id in pairs:
            if str(payload.emoji) == emoji:
                give_role = guild.get_role(int(role_id))
                
                if give_role and member:
                    try:
                        # Handle auto-remove role functionality
                        if auto_remove_role_id:
                            auto_remove_role = guild.get_role(int(auto_remove_role_id))
                            if auto_remove_role and auto_remove_role in member.roles:
                                await member.remove_roles(auto_remove_role, reason="Auto-remove role on reaction role assignment")
                                await log_action(guild.id, "reaction_role", f"🔄 [AUTO-REMOVE] {auto_remove_role.name} removed from {member}")

                        # Add the reaction role
                        if give_role not in member.roles:
                            await member.add_roles(give_role, reason="Reaction role assignment")
                            await log_action(guild.id, "reaction_role", f"🎭 [REACTION ROLE] {give_role.name} added to {member}")

                    except discord.Forbidden:
                        print(f"Missing permissions to modify roles for {member}")
                    except discord.HTTPException as e:
                        print(f"Failed to modify role: {e}")
                break

@bot.event
async def on_raw_reaction_remove(payload):
    """Handle reaction role removal with multiple emoji support"""
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
        member = guild.get_member(payload.user_id)

        if not member:
            return

        # Check for multiple emoji/role pairs
        pairs = reaction_data.get('pairs', [])
        auto_remove_role_id = reaction_data.get('auto_remove_role_id')

        for emoji, role_id in pairs:
            if str(payload.emoji) == emoji:
                remove_role = guild.get_role(int(role_id))
                
                if remove_role and member:
                    try:
                        # Remove the reaction role when unreacting
                        if remove_role in member.roles:
                            await member.remove_roles(remove_role, reason="Reaction role removal")
                            await log_action(guild.id, "reaction_role", f"🎭 [REACTION ROLE] {remove_role.name} removed from {member}")

                        # Restore auto-remove role if enabled and user has no other reaction roles
                        if auto_remove_role_id:
                            auto_remove_role = guild.get_role(int(auto_remove_role_id))
                            if auto_remove_role:
                                # Check if user has any other reaction roles from this message
                                has_other_roles = False
                                for other_emoji, other_role_id in pairs:
                                    if other_emoji != emoji:
                                        other_role = guild.get_role(int(other_role_id))
                                        if other_role and other_role in member.roles:
                                            has_other_roles = True
                                            break

                                # Only restore auto-remove role if user has no other reaction roles
                                if not has_other_roles and auto_remove_role not in member.roles:
                                    await member.add_roles(auto_remove_role, reason="Auto-remove role restoration")
                                    await log_action(guild.id, "reaction_role", f"🔄 [AUTO-RESTORE] {auto_remove_role.name} restored to {member}")

                    except discord.Forbidden:
                        print(f"Missing permissions to modify roles for {member}")
                    except discord.HTTPException as e:
                        print(f"Failed to modify role: {e}")
                break

# List reaction roles command
@bot.tree.command(name="listreactionroles", description="📋 List all active reaction role setups")
async def list_reaction_roles(interaction: discord.Interaction):
    if not await has_permission(interaction, "junior_moderator"):
        await interaction.response.send_message(embed=create_permission_denied_embed("Junior Moderator"), ephemeral=True)
        return

    server_data = await get_server_data(interaction.guild.id)
    reaction_roles = server_data.get('reaction_roles', {})

    if not reaction_roles:
        embed = discord.Embed(
            title="📋 No Reaction Roles Found",
            description="No reaction role setups are currently active in this server.\n\nUse `/reactionrole` or `/quickreactionrole` to create one!",
            color=BrandColors.WARNING
        )
        embed.set_footer(text=BOT_FOOTER)
        await interaction.response.send_message(embed=embed)
        return

    embed = discord.Embed(
        title="📋 **Active Reaction Role Setups**",
        description=f"*Found {len(reaction_roles)} reaction role setup(s)*\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        color=BrandColors.PRIMARY
    )

    count = 0
    for message_id, data in list(reaction_roles.items())[:5]:  # Show max 5
        count += 1
        channel = bot.get_channel(int(data['channel_id']))
        channel_name = channel.mention if channel else f"Unknown Channel"
        
        pairs = data.get('pairs', [])
        auto_remove_role_id = data.get('auto_remove_role_id')
        auto_remove_role = interaction.guild.get_role(int(auto_remove_role_id)) if auto_remove_role_id else None
        
        pair_text = []
        for emoji, role_id in pairs[:3]:  # Show max 3 pairs per setup
            role = interaction.guild.get_role(int(role_id))
            role_name = role.mention if role else "Unknown Role"
            pair_text.append(f"{emoji} → {role_name}")

        if len(pairs) > 3:
            pair_text.append(f"... +{len(pairs)-3} more")

        field_value = f"**Channel:** {channel_name}\n**Pairs:** {', '.join(pair_text) if pair_text else 'None'}"
        if auto_remove_role:
            field_value += f"\n**Auto-Remove:** {auto_remove_role.mention}"

        embed.add_field(
            name=f"#{count} Message ID: {message_id}",
            value=field_value,
            inline=False
        )

    if len(reaction_roles) > 5:
        embed.add_field(
            name="📊 Additional Setups",
            value=f"*{len(reaction_roles) - 5} more setups not shown*",
            inline=False
        )

    embed.set_footer(text=BOT_FOOTER, icon_url=bot.user.display_avatar.url)
    await interaction.response.send_message(embed=embed)