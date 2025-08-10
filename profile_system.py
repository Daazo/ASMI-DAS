
import discord
from discord.ext import commands
from discord import app_commands
from main import bot, db, get_server_data
from PIL import Image, ImageDraw, ImageFont
import io
import requests
import aiohttp

@bot.tree.command(name="profile", description="🖼️ Show your profile card with karma and stats")
@app_commands.describe(user="User to show profile for (optional)")
async def profile_command(interaction: discord.Interaction, user: discord.Member = None):
    target_user = user or interaction.user
    
    # Get user karma data
    karma_data = {"karma": 0, "rank": "N/A"}
    if db:
        user_karma = await db.karma.find_one({'user_id': str(target_user.id), 'guild_id': str(interaction.guild.id)})
        if user_karma:
            karma_data["karma"] = user_karma.get('karma', 0)
            
            # Calculate rank
            all_karma = await db.karma.find({'guild_id': str(interaction.guild.id)}).sort('karma', -1).to_list(length=None)
            for i, k in enumerate(all_karma, 1):
                if k['user_id'] == str(target_user.id):
                    karma_data["rank"] = f"#{i}"
                    break
    
    # Create profile embed
    embed = discord.Embed(
        title=f"🖼️ {target_user.display_name}'s Profile",
        color=target_user.color if target_user.color.value != 0 else 0x3498db
    )
    
    embed.set_thumbnail(url=target_user.display_avatar.url)
    
    # Calculate member position
    members_by_join = sorted(interaction.guild.members, key=lambda m: m.joined_at)
    join_position = members_by_join.index(target_user) + 1
    
    embed.add_field(name="✨ Karma", value=f"**{karma_data['karma']}** points", inline=True)
    embed.add_field(name="📈 Server Rank", value=karma_data['rank'], inline=True)
    embed.add_field(name="🏆 Join Position", value=f"#{join_position}", inline=True)
    
    embed.add_field(
        name="📅 Joined Server", 
        value=f"{discord.utils.format_dt(target_user.joined_at, 'D')}", 
        inline=True
    )
    embed.add_field(
        name="📅 Account Created", 
        value=f"{discord.utils.format_dt(target_user.created_at, 'D')}", 
        inline=True
    )
    embed.add_field(
        name="🎭 Roles", 
        value=f"{len(target_user.roles)-1}", 
        inline=True
    )
    
    # Calculate next milestone
    next_milestone = ((karma_data['karma'] // 50) + 1) * 50
    progress = karma_data['karma'] % 50
    progress_bar = "▓" * (progress // 5) + "░" * ((50 - progress) // 5)
    
    embed.add_field(
        name="🎯 Next Milestone", 
        value=f"{karma_data['karma']}/{next_milestone}\n`{progress_bar}`", 
        inline=False
    )
    
    # Add birthday if set
    if db:
        birthday_data = await db.birthdays.find_one({'user_id': str(target_user.id)})
        if birthday_data:
            birthday = birthday_data['birthday']
            day, month = birthday.split('-')
            month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            embed.add_field(
                name="🎂 Birthday", 
                value=f"{int(day)} {month_names[int(month)]}", 
                inline=True
            )
    
    embed.set_footer(text="🌴 ᴠᴀᴀᴢʜᴀ Profile System", icon_url=bot.user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)

async def create_profile_image(user, karma_data):
    """Create a profile image card (optional advanced feature)"""
    # This would create a custom image with PIL
    # For now, we'll use embeds which are more reliable
    pass
