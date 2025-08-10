
import discord
from discord.ext import commands
from discord import app_commands
from main import bot, has_permission, get_server_data, update_server_data, log_action

@bot.tree.command(name="setkarmaemojis", description="✨ Set custom emojis for karma system")
@app_commands.describe(
    positive_emojis="Positive karma emojis (separated by spaces)",
    negative_emojis="Negative karma emojis (separated by spaces)"
)
async def set_karma_emojis(interaction: discord.Interaction, positive_emojis: str, negative_emojis: str = None):
    if not await has_permission(interaction, "main_moderator"):
        await interaction.response.send_message("❌ You need Main Moderator permissions to use this command!", ephemeral=True)
        return
    
    # Parse emojis
    positive_list = positive_emojis.split()
    negative_list = negative_emojis.split() if negative_emojis else []
    
    # Validate emojis
    if len(positive_list) < 1:
        await interaction.response.send_message("❌ You must provide at least 1 positive emoji!", ephemeral=True)
        return
    
    # Save to database
    karma_settings = {
        'custom_karma_emojis': {
            'positive': positive_list,
            'negative': negative_list
        }
    }
    await update_server_data(interaction.guild.id, karma_settings)
    
    embed = discord.Embed(
        title="✨ Custom Karma Emojis Set",
        description=f"**Positive Emojis:** {' '.join(positive_list)}\n**Negative Emojis:** {' '.join(negative_list) if negative_list else 'None'}",
        color=0x43b581
    )
    embed.add_field(
        name="ℹ️ How It Works",
        value="Members can now react with these custom emojis to give/remove karma!",
        inline=False
    )
    embed.set_footer(text="ᴠᴀᴀᴢʜᴀ")
    await interaction.response.send_message(embed=embed)
    
    await log_action(interaction.guild.id, "setup", f"✨ [KARMA EMOJIS] Custom emojis set by {interaction.user}")

@bot.tree.command(name="resetkarmaemojis", description="🔄 Reset karma emojis to default")
async def reset_karma_emojis(interaction: discord.Interaction):
    if not await has_permission(interaction, "main_moderator"):
        await interaction.response.send_message("❌ You need Main Moderator permissions to use this command!", ephemeral=True)
        return
    
    # Remove custom emojis
    server_data = await get_server_data(interaction.guild.id)
    if 'custom_karma_emojis' in server_data:
        del server_data['custom_karma_emojis']
        await update_server_data(interaction.guild.id, server_data)
    
    embed = discord.Embed(
        title="🔄 Karma Emojis Reset",
        description="Karma emojis have been reset to default!\n\n**Default Positive:** 👍 ⭐ ❤️ 🔥 💯 ✨\n**Default Negative:** 👎 💀 😴 🤮 🗿",
        color=0x43b581
    )
    embed.set_footer(text="ᴠᴀᴀᴢʜᴀ")
    await interaction.response.send_message(embed=embed)
    
    await log_action(interaction.guild.id, "setup", f"🔄 [KARMA EMOJIS] Reset to default by {interaction.user}")

# Update the reaction handler in main.py to use custom emojis
async def get_karma_emojis(guild_id):
    """Get karma emojis for a server"""
    server_data = await get_server_data(guild_id)
    custom_emojis = server_data.get('custom_karma_emojis')
    
    if custom_emojis:
        return custom_emojis['positive'], custom_emojis['negative']
    else:
        # Default emojis
        positive = ['👍', '⭐', '❤️', '🔥', '💯', '✨']
        negative = ['👎', '💀', '😴', '🤮', '🗿']
        return positive, negative
