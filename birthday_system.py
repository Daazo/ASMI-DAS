
import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
from datetime import datetime, timedelta
from main import bot, get_server_data, update_server_data, log_action, db
import random

# Birthday quotes for celebrations
BIRTHDAY_QUOTES = [
    "🎂 Another year of awesome! Happy Birthday! 🎉",
    "🌟 Wishing you joy, happiness and all the best on your special day! 🎂",
    "🎉 May your birthday be filled with wonderful surprises! 🎈",
    "🎂 Celebrating you today and always! Happy Birthday! ✨",
    "🌈 Hope your birthday brings you lots of joy and laughter! 🎊",
    "🎁 Another year, another reason to celebrate! Happy Birthday! 🎉",
    "🎂 May this new year of life bring you endless happiness! 🌟",
    "🎈 Sending you birthday wishes filled with love and joy! 💖"
]

async def get_user_birthday(user_id):
    """Get user's birthday from database"""
    if db is not None:
        user_data = await db.birthdays.find_one({'user_id': str(user_id)})
        return user_data.get('birthday') if user_data else None
    return None

async def set_user_birthday(user_id, birthday):
    """Set user's birthday in database"""
    if db is not None:
        await db.birthdays.update_one(
            {'user_id': str(user_id)},
            {'$set': {'birthday': birthday}},
            upsert=True
        )

async def remove_user_birthday(user_id):
    """Remove user's birthday from database"""
    if db is not None:
        await db.birthdays.delete_one({'user_id': str(user_id)})

async def get_birthday_channel(guild_id):
    """Get birthday announcement channel"""
    server_data = await get_server_data(guild_id)
    return server_data.get('birthday_channel')

async def set_birthday_channel(guild_id, channel_id):
    """Set birthday announcement channel"""
    await update_server_data(guild_id, {'birthday_channel': str(channel_id)})

@bot.tree.command(name="setbirthday", description="🎂 Set your birthday (DD-MM format)")
@app_commands.describe(day="Day of your birthday (1-31)", month="Month of your birthday (1-12)")
async def set_birthday(interaction: discord.Interaction, day: int, month: int):
    # Validate input
    if not (1 <= day <= 31) or not (1 <= month <= 12):
        embed = discord.Embed(
            title="❌ Invalid Date",
            description="Please enter a valid date!\n**Day:** 1-31\n**Month:** 1-12",
            color=0xe74c3c
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Check for valid date combinations
    if month in [4, 6, 9, 11] and day > 30:
        await interaction.response.send_message("❌ That month only has 30 days!", ephemeral=True)
        return
    if month == 2 and day > 29:
        await interaction.response.send_message("❌ February only has 28-29 days!", ephemeral=True)
        return
    
    birthday = f"{day:02d}-{month:02d}"
    await set_user_birthday(interaction.user.id, birthday)
    
    embed = discord.Embed(
        title="🎂 Birthday Set Successfully!",
        description=f"**Your birthday:** {day}/{month}\n\n🎉 You'll receive birthday wishes and **+10 karma** on your special day!",
        color=0x43b581
    )
    embed.set_footer(text="ᴠᴀᴀᴢʜᴀ", icon_url=bot.user.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="mybirthday", description="🎂 Check your saved birthday")
async def my_birthday(interaction: discord.Interaction):
    birthday = await get_user_birthday(interaction.user.id)
    
    if not birthday:
        embed = discord.Embed(
            title="🎂 No Birthday Set",
            description="You haven't set your birthday yet!\n\nUse `/setbirthday day:15 month:6` to set it.",
            color=0xf39c12
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    day, month = birthday.split('-')
    month_names = ["", "January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]
    
    embed = discord.Embed(
        title="🎂 Your Birthday",
        description=f"**Date:** {int(day)} {month_names[int(month)]}\n\n🎉 We'll celebrate with you when the day comes!",
        color=0x3498db
    )
    embed.set_footer(text="ᴠᴀᴀᴢʜᴀ", icon_url=bot.user.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="birthdaychannel", description="🎂 Set birthday announcement channel")
@app_commands.describe(channel="Channel for birthday announcements")
async def birthday_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    from main import has_permission
    if not await has_permission(interaction, "main_moderator"):
        await interaction.response.send_message("❌ You need Main Moderator permissions to use this command!", ephemeral=True)
        return
    
    await set_birthday_channel(interaction.guild.id, channel.id)
    
    embed = discord.Embed(
        title="🎂 Birthday Channel Set",
        description=f"Birthday announcements will be sent to {channel.mention}!",
        color=0x43b581
    )
    embed.set_footer(text="ᴠᴀᴀᴢʜᴀ")
    await interaction.response.send_message(embed=embed)
    
    await log_action(interaction.guild.id, "setup", f"🎂 [BIRTHDAY] Channel set to {channel.name} by {interaction.user}")

@bot.tree.command(name="removebirthday", description="🗑️ Remove your saved birthday")
async def remove_birthday(interaction: discord.Interaction):
    birthday = await get_user_birthday(interaction.user.id)
    
    if not birthday:
        await interaction.response.send_message("❌ You don't have a birthday set!", ephemeral=True)
        return
    
    await remove_user_birthday(interaction.user.id)
    
    embed = discord.Embed(
        title="🗑️ Birthday Removed",
        description="Your birthday has been removed from the system.",
        color=0xe74c3c
    )
    embed.set_footer(text="ᴠᴀᴀᴢʜᴀ")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tasks.loop(hours=24)
async def check_birthdays():
    """Check for birthdays daily at midnight"""
    if not db:
        return
    
    today = datetime.now().strftime("%d-%m")
    
    # Get all users with today's birthday
    birthday_users = await db.birthdays.find({'birthday': today}).to_list(length=None)
    
    for user_data in birthday_users:
        user_id = int(user_data['user_id'])
        user = bot.get_user(user_id)
        if not user:
            continue
        
        # Check all servers the user is in
        for guild in bot.guilds:
            if guild.get_member(user_id):
                birthday_channel_id = await get_birthday_channel(guild.id)
                if birthday_channel_id:
                    channel = bot.get_channel(int(birthday_channel_id))
                    if channel:
                        # Give +10 karma birthday bonus
                        if db:
                            await db.karma.update_one(
                                {'user_id': str(user_id), 'guild_id': str(guild.id)},
                                {'$inc': {'karma': 10}},
                                upsert=True
                            )
                        
                        # Send birthday message
                        quote = random.choice(BIRTHDAY_QUOTES)
                        embed = discord.Embed(
                            title="🎂 **HAPPY BIRTHDAY!** 🎂",
                            description=f"**{quote}**\n\n🎉 **Today we celebrate {user.mention}!** 🎉\n\n🎁 **Birthday Gift:** +10 Karma! ✨",
                            color=0xf39c12
                        )
                        embed.set_thumbnail(url=user.display_avatar.url)
                        embed.set_footer(text="🌴 ᴠᴀᴀᴢʜᴀ Birthday System", icon_url=bot.user.display_avatar.url)
                        
                        try:
                            await channel.send(f"🎂 {user.mention}", embed=embed)
                        except:
                            pass

@check_birthdays.before_loop
async def before_birthday_check():
    await bot.wait_until_ready()

# Start birthday checking task
check_birthdays.start()
