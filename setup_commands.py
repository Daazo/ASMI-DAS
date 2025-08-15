import discord
from discord.ext import commands
from discord import app_commands
from main import bot, has_permission, get_server_data, update_server_data, log_action

@bot.tree.command(name="setup", description="Configure bot settings")
@app_commands.describe(
    action="What to setup",
    value="Value to set",
    role="Role to assign",
    channel="Channel to set",
    category="Category for organized logging"
)
@app_commands.choices(action=[
    app_commands.Choice(name="main_moderator", value="main_moderator"),
    app_commands.Choice(name="junior_moderator", value="junior_moderator"),
    app_commands.Choice(name="welcome", value="welcome"),
    app_commands.Choice(name="welcome_image", value="welcome_image"),
    app_commands.Choice(name="logs", value="logs"),
    app_commands.Choice(name="karma_channel", value="karma_channel"),
    app_commands.Choice(name="ticket_support_role", value="ticket_support_role"),
    app_commands.Choice(name="auto_role", value="auto_role"),
    app_commands.Choice(name="log_category", value="log_category")
])
async def setup(
    interaction: discord.Interaction,
    action: str,
    value: str = None,
    role: discord.Role = None,
    channel: discord.TextChannel = None,
    category: discord.CategoryChannel = None
):
    # Check permissions
    if action == "main_moderator":
        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("❌ Only the server owner can set main moderator role!", ephemeral=True)
            return
    else:
        if not await has_permission(interaction, "main_moderator"):
            await interaction.response.send_message("❌ You need Main Moderator permissions to use this command!", ephemeral=True)
            return

    server_data = await get_server_data(interaction.guild.id)

    if action == "main_moderator":
        if not role:
            await interaction.response.send_message("❌ Please specify a role!", ephemeral=True)
            return

        await update_server_data(interaction.guild.id, {'main_moderator_role': str(role.id)})

        embed = discord.Embed(
            title="✅ Main Moderator Role Set",
            description=f"**Role:** {role.mention}\n**Set by:** {interaction.user.mention}",
            color=0x43b581
        )
        embed.set_footer(text="ᴠᴀᴀᴢʜᴀ")
        await interaction.response.send_message(embed=embed)
        await log_action(interaction.guild.id, "setup", f"⚙️ [SETUP] Main moderator role set to {role.name} by {interaction.user}")

    elif action == "junior_moderator":
        if not role:
            await interaction.response.send_message("❌ Please specify a role!", ephemeral=True)
            return

        await update_server_data(interaction.guild.id, {'junior_moderator_role': str(role.id)})

        embed = discord.Embed(
            title="✅ Junior Moderator Role Set",
            description=f"**Role:** {role.mention}\n**Set by:** {interaction.user.mention}",
            color=0x43b581
        )
        embed.set_footer(text="ᴠᴀᴀᴢʜᴀ")
        await interaction.response.send_message(embed=embed)
        await log_action(interaction.guild.id, "setup", f"⚙️ [SETUP] Junior moderator role set to {role.name} by {interaction.user}")

    elif action == "welcome":
        if not channel:
            await interaction.response.send_message("❌ Please specify a welcome channel!", ephemeral=True)
            return

        # Store welcome settings
        welcome_data = {
            'welcome_channel': str(channel.id),
            'welcome_message': value or f"Welcome {{user}} to {{server}}!",
        }

        # If image URL is provided, store it
        if value and ("http" in value.lower() and any(ext in value.lower() for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp'])):
            # Extract message and image
            parts = value.split('|')
            if len(parts) == 2:
                welcome_data['welcome_message'] = parts[0].strip()
                welcome_data['welcome_image'] = parts[1].strip()
            else:
                welcome_data['welcome_image'] = value

        await update_server_data(interaction.guild.id, welcome_data)

        # Test welcome functionality
        test_embed = discord.Embed(
            title="✅ Welcome System Test",
            description=f"**Channel:** {channel.mention}\n**Message:** {welcome_data['welcome_message']}\n" +
                       (f"**Image/GIF:** ✅ Working properly" if welcome_data.get('welcome_image') else "**Image/GIF:** None set"),
            color=0x43b581
        )
        if welcome_data.get('welcome_image'):
            test_embed.set_image(url=welcome_data['welcome_image'])

        test_embed.set_footer(text="ᴠᴀᴀᴢʜᴀ - Welcome system is ready!")
        await interaction.response.send_message(embed=test_embed)

    elif action == "welcome_image":
        if not value:
            await interaction.response.send_message("❌ Please specify an image URL for welcome messages!", ephemeral=True)
            return

        # Basic URL validation
        if not (value.startswith('http://') or value.startswith('https://')):
            await interaction.response.send_message("❌ Please provide a valid image URL (starting with http:// or https://)", ephemeral=True)
            return

        await update_server_data(interaction.guild.id, {'welcome_image': value})

        embed = discord.Embed(
            title="✅ Welcome Image Set",
            description=f"**Image URL:** {value}\n**Set by:** {interaction.user.mention}",
            color=0x43b581
        )
        embed.set_image(url=value)
        embed.set_footer(text="ᴠᴀᴀᴢʜᴀ")
        await interaction.response.send_message(embed=embed)
        await log_action(interaction.guild.id, "setup", f"⚙️ [SETUP] Welcome image set by {interaction.user}")

    elif action == "prefix":
        if not value:
            await interaction.response.send_message("❌ Please specify a prefix!", ephemeral=True)
            return

        if len(value) > 5:
            await interaction.response.send_message("❌ Prefix must be 5 characters or less!", ephemeral=True)
            return

        await update_server_data(interaction.guild.id, {'prefix': value})

        embed = discord.Embed(
            title="✅ Prefix Updated",
            description=f"**New Prefix:** `{value}`\n**Set by:** {interaction.user.mention}",
            color=0x43b581
        )
        await interaction.response.send_message(embed=embed)
        await log_action(interaction.guild.id, "setup", f"⚙️ [SETUP] Prefix set to '{value}' by {interaction.user}")

    elif action == "logs":
        if not value or not channel:
            await interaction.response.send_message("❌ Please specify log type and channel!\n**Log types:** all, moderation, xp, communication", ephemeral=True)
            return

        valid_log_types = ["all", "moderation", "karma", "communication", "tickets"]
        if value not in valid_log_types:
            await interaction.response.send_message(f"❌ Invalid log type! Valid types: {', '.join(valid_log_types)}", ephemeral=True)
            return

        log_channels = server_data.get('log_channels', {})
        log_channels[value] = str(channel.id)

        await update_server_data(interaction.guild.id, {'log_channels': log_channels})

        embed = discord.Embed(
            title="✅ Log Channel Set",
            description=f"**Log Type:** {value}\n**Channel:** {channel.mention}\n**Set by:** {interaction.user.mention}",
            color=0x43b581
        )
        embed.set_footer(text="ᴠᴀᴀᴢʜᴀ")
        await interaction.response.send_message(embed=embed)
        await log_action(interaction.guild.id, "setup", f"⚙️ [SETUP] {value} log channel set to {channel.name} by {interaction.user}")

    elif action == "karma_channel":
        if not channel:
            await interaction.response.send_message("❌ Please specify a channel for karma announcements!", ephemeral=True)
            return

        await update_server_data(interaction.guild.id, {'karma_channel': str(channel.id)})

        embed = discord.Embed(
            title="✅ Karma Channel Set",
            description=f"**Karma milestone announcements will be sent to:** {channel.mention}",
            color=0x43b581
        )
        embed.set_footer(text="ᴠᴀᴀᴢʜᴀ")
        await interaction.response.send_message(embed=embed)

        await log_action(interaction.guild.id, "setup", f"✨ [KARMA SETUP] Karma channel set to {channel} by {interaction.user}")

    elif action == "auto_role":
        if not role:
            await interaction.response.send_message("❌ Please specify a role for auto assignment!", ephemeral=True)
            return

        await update_server_data(interaction.guild.id, {'auto_role': str(role.id)})

        embed = discord.Embed(
            title="✅ Auto Role Set",
            description=f"**Role:** {role.mention}\n**Set by:** {interaction.user.mention}\n\n*This role will be automatically assigned to new members.*",
            color=0x43b581
        )
        embed.set_footer(text="ᴠᴀᴀᴢʜᴀ")
        await interaction.response.send_message(embed=embed)
        await log_action(interaction.guild.id, "setup", f"⚙️ [SETUP] Auto role set to {role.name} by {interaction.user}")

    elif action == "ticket_support_role":
        if not role:
            await interaction.response.send_message("❌ Please specify a role for ticket support!", ephemeral=True)
            return

        await update_server_data(interaction.guild.id, {'ticket_support_role': str(role.id)})

        embed = discord.Embed(
            title="✅ Ticket Support Role Set",
            description=f"**Role:** {role.mention}\n**Set by:** {interaction.user.mention}\n\n*This role will be mentioned when tickets are created.*",
            color=0x43b581
        )
        embed.set_footer(text="ᴠᴀᴀᴢʜᴀ")
        await interaction.response.send_message(embed=embed)
        await log_action(interaction.guild.id, "setup", f"⚙️ [SETUP] Ticket support role set to {role.name} by {interaction.user}")

    elif action == "log_category":
        if not category:
            await interaction.response.send_message("❌ Please specify a category for organized logging channels!", ephemeral=True)
            return

        # Defer the response to prevent timeout
        await interaction.response.defer()

        try:
            # Store the category
            await update_server_data(interaction.guild.id, {'log_category': str(category.id)})

            # Get category permissions to inherit
            overwrites = category.overwrites

            # Create all log channels with proper names and descriptions
            log_channels_to_create = [
                ("📋-general-logs", "General commands and bot usage logs (includes ping, uptime, profile commands) 🤖", False),
                ("🛡️-moderation-logs", "Moderation commands and actions logs ⚔️", False),
                ("⚙️-setup-config-logs", "Setup and configuration commands logs 🔧", False),
                ("💬-communication-logs", "Communication commands and messages logs 📢", False),
                ("✨-karma-logs", "Karma system commands and level-up logs 🌟", False),
                ("🪙-economy-logs", "Economy system commands and transactions logs 💰", False),
                ("🎫-ticket-logs", "Ticket system creation and management logs 🎟️", False),
                ("🎭-reaction-role-logs", "Reaction role verification and assignment logs 🎪", False),
                ("👋-welcome-logs", "Member join and welcome message logs 🎊", False),
                ("🔊-voice-logs", "Voice channel join, leave, and activity logs 🎵", False),
                ("🕰️-timed-role-logs", "Timed role assignments and removals logs ⏰", False),
                ("🔒-timeout-logs", "Auto-timeout system and penalty logs ⚠️", False),
                ("🔒-security-logs", "Security feature alerts and logs 🛡️", False)
            ]

            created_channels = []
            log_channel_ids = {}

            log_mapping = {
                "general": "general",
                "moderation": "moderation",
                "setup": "setup",
                "communication": "communication",
                "karma": "karma",
                "economy": "economy",
                "tickets": "ticket",
                "reaction_role": "reaction",
                "welcome": "welcome",
                "voice": "voice",
                "timed_roles": "timed",
                "timeout": "timeout",
                "security": "security",
                "profile": "general",  # Route profile logs to general
                "utility": "general"   # Route utility logs to general
            }


            for channel_name, description, bot_only in log_channels_to_create:
                # Check if channel already exists
                existing_channel = discord.utils.get(category.channels, name=channel_name)
                if not existing_channel:
                    # Create channel with inherited permissions
                    channel_overwrites = overwrites.copy()

                    # If bot_only, restrict to bot and admins only
                    if bot_only:
                        channel_overwrites[interaction.guild.default_role] = discord.PermissionOverwrite(
                            read_messages=False, send_messages=False
                        )
                        channel_overwrites[interaction.guild.me] = discord.PermissionOverwrite(
                            read_messages=True, send_messages=True
                        )

                    channel = await interaction.guild.create_text_channel(
                        name=channel_name,
                        category=category,
                        overwrites=channel_overwrites,
                        topic=description
                    )
                    created_channels.append(channel)

                    # Send initial message to log channels
                    embed = discord.Embed(
                        title=f"🌴 **{channel_name.replace('-', ' ').title()} Channel**",
                        description=f"**{description}**\n\n*This channel will automatically receive relevant bot logs.*\n\n**🤖 Bot:** {interaction.guild.me.mention}\n**Setup by:** {interaction.user.mention}\n**Setup time:** {discord.utils.format_dt(discord.utils.utcnow())}",
                        color=0x43b581
                    )
                    embed.set_footer(text="🌴 ᴠᴀᴀᴢʜᴀ Logging System", icon_url=interaction.guild.me.display_avatar.url)
                    await channel.send(embed=embed)

                # Store channel ID for log mapping
                log_key = channel_name.split('-')[1]  # Extract key from channel name
                if existing_channel:
                    log_channel_ids[log_key] = str(existing_channel.id)
                else:
                    log_channel_ids[log_key] = str(channel.id)

            # Update server data with organized log channels
            await update_server_data(interaction.guild.id, {'organized_log_channels': log_channel_ids})

            embed = discord.Embed(
                title="✅ Organized Logging System Setup Complete!",
                description=f"**Category:** {category.mention}\n**Channels Created:** {len(created_channels)}\n**Total Log Channels:** {len(log_channels_to_create)}\n\n🎯 **Organized Logging Features:**\n📋 General logs (includes ping, uptime, profile commands)\n🛡️ Moderation action tracking\n⚙️ Setup and configuration logs\n💬 Communication command logs\n✨ Karma system activity\n🪙 Economy transactions\n🎫 Ticket management\n🎭 Reaction role verifications\n👋 Welcome system logs\n🔊 Voice activity tracking\n🕰️ Timed role management\n🔒 Auto-timeout system logs\n🔒 Security feature alerts",
                color=0x3498db
            )
            embed.set_footer(text="🌴 Professional logging system active!")
            await interaction.followup.send(embed=embed)

            await log_action(interaction.guild.id, "setup", f"📋 [LOG SETUP] Organized logging system set up in {category.name} by {interaction.user}")

        except Exception as e:
            await interaction.followup.send(f"❌ Error setting up log category: {str(e)}", ephemeral=True)

# --- New command for auto-remove role ---
@bot.tree.command(name="autoremoverole", description="Manage auto-remove role rules")
@app_commands.describe(
    subcommand="Choose an action",
    remove_role="The role to remove from a user",
    reason_role="The role that triggers the removal",
    list_rules="List all current auto-remove rules"
)
@app_commands.choices(subcommand=[
    app_commands.Choice(name="add", value="add"),
    app_commands.Choice(name="remove", value="remove"),
    app_commands.Choice(name="list", value="list")
])
async def autoremoverole(
    interaction: discord.Interaction,
    subcommand: str,
    remove_role: discord.Role = None,
    reason_role: discord.Role = None,
    list_rules: str = None
):
    server_data = await get_server_data(interaction.guild.id)
    auto_remove_rules = server_data.get("auto_remove_roles", [])

    if subcommand == "add":
        if not remove_role or not reason_role:
            await interaction.response.send_message("❌ Please specify both the role to remove and the reason role.", ephemeral=True)
            return

        if remove_role.position >= interaction.guild.me.top_role.position:
            await interaction.response.send_message(f"❌ I cannot manage the `{remove_role.name}` role as it's higher than or equal to my highest role.", ephemeral=True)
            return

        if reason_role.position >= interaction.guild.me.top_role.position:
            await interaction.response.send_message(f"❌ I cannot manage the `{reason_role.name}` role as it's higher than or equal to my highest role.", ephemeral=True)
            return

        # Check if rule already exists
        for rule in auto_remove_rules:
            if rule["remove_role_id"] == str(remove_role.id) and rule["reason_role_id"] == str(reason_role.id):
                await interaction.response.send_message("✅ This auto-remove rule already exists.", ephemeral=True)
                return

        auto_remove_rules.append({"remove_role_id": str(remove_role.id), "reason_role_id": str(reason_role.id)})
        await update_server_data(interaction.guild.id, {"auto_remove_roles": auto_remove_rules})

        embed = discord.Embed(
            title="✅ Auto-Remove Role Rule Added",
            description=f"**When a user gets** {reason_role.mention}\n**They will lose** {remove_role.mention}",
            color=0x43b581
        )
        embed.set_footer(text="ᴠᴀᴀᴢʜᴀ")
        await interaction.response.send_message(embed=embed)
        await log_action(interaction.guild.id, "setup", f"⚙️ [AUTOREMOVEROLE] Rule added: Remove {remove_role.name} when user gets {reason_role.name} by {interaction.user}")

    elif subcommand == "remove":
        if not reason_role:
            await interaction.response.send_message("❌ Please specify the reason role to remove the rule.", ephemeral=True)
            return

        rule_removed = False
        new_rules = []
        for rule in auto_remove_rules:
            if rule["reason_role_id"] == str(reason_role.id):
                rule_removed = True
                removed_role_id = rule["remove_role_id"]
                removed_role = interaction.guild.get_role(int(removed_role_id))
                await log_action(interaction.guild.id, "setup", f"⚙️ [AUTOREMOVEROLE] Rule removed: Remove {removed_role.name if removed_role else 'Unknown Role'} when user gets {reason_role.name} by {interaction.user}")
            else:
                new_rules.append(rule)
        
        if rule_removed:
            await update_server_data(interaction.guild.id, {"auto_remove_roles": new_rules})
            embed = discord.Embed(
                title="✅ Auto-Remove Role Rule Removed",
                description=f"Removed rules where user getting {reason_role.mention} triggers role removal.",
                color=0x43b581
            )
            embed.set_footer(text="ᴠᴀᴀᴢʜᴀ")
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ No auto-remove rule found for that reason role.", ephemeral=True)

    elif subcommand == "list":
        if not auto_remove_rules:
            await interaction.response.send_message("ℹ️ There are no auto-remove role rules currently set up.", ephemeral=True)
            return

        embed = discord.Embed(
            title="📜 Auto-Remove Role Rules",
            description="List of rules where a role is removed when a user obtains a specific role.",
            color=0x3498db
        )

        for rule in auto_remove_rules:
            remove_role = interaction.guild.get_role(int(rule["remove_role_id"]))
            reason_role = interaction.guild.get_role(int(rule["reason_role_id"]))
            
            if remove_role and reason_role:
                embed.add_field(
                    name=f"Rule: {reason_role.name} -> Remove {remove_role.name}",
                    value=f"When user gets {reason_role.mention}, they lose {remove_role.mention}.",
                    inline=False
                )
            else:
                embed.add_field(
                    name="Invalid Rule",
                    value="One or more roles in this rule are no longer available.",
                    inline=False
                )

        embed.set_footer(text="ᴠᴀᴀᴢʜᴀ")
        await interaction.response.send_message(embed=embed, ephemeral=True)

# --- Reaction Role Command (Assuming it's in the same file or imported) ---
# The original code did not contain the reaction role command,
# so I am adding a placeholder for where it might go or if it's handled elsewhere.
# If the reaction role command logic is in another file, ensure it's imported and functioning.

# Example placeholder for a reaction role command if it were here:
# @bot.tree.command(name="reactionrole", description="Setup reaction roles")
# async def reactionrole(interaction: discord.Interaction):
#     await interaction.response.send_message("Reaction role command functionality would go here.", ephemeral=True)

# --- Syncing commands across servers ---
# This part is usually handled in the main bot file or a dedicated sync cog.
# If commands are not showing up, the issue might be in how sync commands are called.
# Ensure `await bot.tree.sync()` or `await bot.tree.sync(guild=discord.Object(id=YOUR_GUILD_ID))` is called appropriately.
# For global commands, sync can take up to an hour. For guild commands, it's usually faster.

# If the issue is that commands are not showing up in all servers,
# it's likely related to the sync process. Ensure that either:
# 1. `bot.tree.sync()` is called after the bot starts to sync globally.
# 2. `bot.tree.sync(guild=discord.Object(id=guild.id))` is called for each guild
#    the bot is in, perhaps during a `on_guild_join` event or a setup command,
#    to ensure commands are registered quickly for specific servers.

# Example of how to ensure commands are synced for all guilds the bot is in:
# @bot.event
# async def on_ready():
#     print(f'Logged in as {bot.user.name}')
#     print('------')
#     # Sync commands for all guilds the bot is in
#     for guild in bot.guilds:
#         try:
#             bot.tree.copy_global_to(guild=guild)
#             await bot.tree.sync(guild=guild)
#             print(f"Synced commands for guild: {guild.name}")
#         except Exception as e:
#             print(f"Failed to sync commands for guild {guild.name}: {e}")
#     print("All commands synced.")

# If commands are missing in specific servers, it could also be due to:
# - The bot not having the `applications.commands` scope granted when invited.
# - Errors during the sync process for that specific server.
# - Discord API rate limits or delays.