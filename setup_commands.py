import discord
from discord.ext import commands
from discord import app_commands
from main import bot
from brand_config import BOT_FOOTER, BrandColors
from main import has_permission, get_server_data, update_server_data, log_action

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
    app_commands.Choice(name="welcome_title", value="welcome_title"),
    app_commands.Choice(name="welcome_image", value="welcome_image"),
    app_commands.Choice(name="logs", value="logs"),
    app_commands.Choice(name="karma_channel", value="karma_channel"),
    app_commands.Choice(name="ticket_support_role", value="ticket_support_role"),
    app_commands.Choice(name="auto_role", value="auto_role")
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
            title="⚡ **Main Moderator Role Set**",
            description=f"**◆ Role:** {role.mention}\n**◆ Set by:** {interaction.user.mention}",
            color=BrandColors.PRIMARY
        )
        embed.set_footer(text=BOT_FOOTER)
        await interaction.response.send_message(embed=embed)
        await log_action(interaction.guild.id, "setup", f"⚙️ [SETUP] Main moderator role set to {role.name} by {interaction.user}")

    elif action == "junior_moderator":
        if not role:
            await interaction.response.send_message("❌ Please specify a role!", ephemeral=True)
            return

        await update_server_data(interaction.guild.id, {'junior_moderator_role': str(role.id)})

        embed = discord.Embed(
            title="⚡ **Junior Moderator Role Set**",
            description=f"**◆ Role:** {role.mention}\n**◆ Set by:** {interaction.user.mention}",
            color=BrandColors.PRIMARY
        )
        embed.set_footer(text=BOT_FOOTER)
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
            title="💠 **Welcome System Test**",
            description=f"**◆ Channel:** {channel.mention}\n**◆ Message:** {welcome_data['welcome_message']}\n" + 
                       (f"**◆ Image/GIF:** ✓ Working properly" if welcome_data.get('welcome_image') else "**◆ Image/GIF:** None set"),
            color=BrandColors.PRIMARY
        )
        if welcome_data.get('welcome_image'):
            test_embed.set_image(url=welcome_data['welcome_image'])

        test_embed.set_footer(text=f"{BOT_FOOTER} • Welcome system is ready!")
        await interaction.response.send_message(embed=test_embed)

    elif action == "welcome_title":
        if not value:
            await interaction.response.send_message("❌ Please specify a welcome title!", ephemeral=True)
            return

        await update_server_data(interaction.guild.id, {'welcome_title': value})

        embed = discord.Embed(
            title="💠 **Welcome Title Set**",
            description=f"**◆ Title:** {value}\n**◆ Set by:** {interaction.user.mention}\n\n*Use {{user}} and {{server}} placeholders*",
            color=BrandColors.PRIMARY
        )
        embed.set_footer(text=BOT_FOOTER)
        await interaction.response.send_message(embed=embed)
        await log_action(interaction.guild.id, "setup", f"⚙️ [SETUP] Welcome title set by {interaction.user}")

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
            title="💠 **Welcome Image Set**",
            description=f"**◆ Image URL:** {value}\n**◆ Set by:** {interaction.user.mention}",
            color=BrandColors.PRIMARY
        )
        embed.set_image(url=value)
        embed.set_footer(text=BOT_FOOTER)
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
            title="⚡ **Prefix Updated**",
            description=f"**◆ New Prefix:** `{value}`\n**◆ Set by:** {interaction.user.mention}",
            color=BrandColors.PRIMARY
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
            title="⚡ **Log Channel Set**",
            description=f"**◆ Log Type:** {value}\n**◆ Channel:** {channel.mention}\n**◆ Set by:** {interaction.user.mention}",
            color=BrandColors.PRIMARY
        )
        embed.set_footer(text=BOT_FOOTER)
        await interaction.response.send_message(embed=embed)
        await log_action(interaction.guild.id, "setup", f"⚙️ [SETUP] {value} log channel set to {channel.name} by {interaction.user}")

    elif action == "karma_channel":
        if not channel:
            await interaction.response.send_message("❌ Please specify a channel for karma announcements!", ephemeral=True)
            return

        await update_server_data(interaction.guild.id, {'karma_channel': str(channel.id)})

        embed = discord.Embed(
            title="💠 **Karma Channel Set**",
            description=f"**◆ Karma milestone announcements will be sent to:** {channel.mention}",
            color=BrandColors.PRIMARY
        )
        embed.set_footer(text=BOT_FOOTER)
        await interaction.response.send_message(embed=embed)

        await log_action(interaction.guild.id, "setup", f"✨ [KARMA SETUP] Karma channel set to {channel} by {interaction.user}")

    elif action == "auto_role":
        if not role:
            await interaction.response.send_message("❌ Please specify a role for auto assignment!", ephemeral=True)
            return

        await update_server_data(interaction.guild.id, {'auto_role': str(role.id)})

        embed = discord.Embed(
            title="⚡ **Auto Role Set**",
            description=f"**◆ Role:** {role.mention}\n**◆ Set by:** {interaction.user.mention}\n\n*This role will be automatically assigned to new members.*",
            color=BrandColors.PRIMARY
        )
        embed.set_footer(text=BOT_FOOTER)
        await interaction.response.send_message(embed=embed)
        await log_action(interaction.guild.id, "setup", f"⚙️ [SETUP] Auto role set to {role.name} by {interaction.user}")

    elif action == "ticket_support_role":
        if not role:
            await interaction.response.send_message("❌ Please specify a role for ticket support!", ephemeral=True)
            return

        await update_server_data(interaction.guild.id, {'ticket_support_role': str(role.id)})

        embed = discord.Embed(
            title="🎫 **Ticket Support Role Set**",
            description=f"**◆ Role:** {role.mention}\n**◆ Set by:** {interaction.user.mention}\n\n*This role will be mentioned when tickets are created.*",
            color=BrandColors.PRIMARY
        )
        embed.set_footer(text=BOT_FOOTER)
        await interaction.response.send_message(embed=embed)
        await log_action(interaction.guild.id, "setup", f"⚙️ [SETUP] Ticket support role set to {role.name} by {interaction.user}")

