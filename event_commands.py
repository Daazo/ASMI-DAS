import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
from main import bot, has_permission, log_action, get_server_data, update_server_data, db
from brand_config import BOT_FOOTER, BrandColors, VisualElements
from datetime import datetime, timedelta

print("✅ Event system module loading...")

# Helper functions for event role permissions
async def has_event_role_permission(interaction):
    """Check if user has event role or higher permissions"""
    if interaction.user.id == interaction.guild.owner_id:
        return True
    
    server_data = await get_server_data(interaction.guild.id)
    event_role_id = server_data.get('event_role')
    
    # Check if user has event role
    if event_role_id:
        event_role = interaction.guild.get_role(int(event_role_id))
        if event_role and event_role in interaction.user.roles:
            return True
    
    # Check if user is main moderator or junior moderator
    if await has_permission(interaction, "main_moderator"):
        return True
    if await has_permission(interaction, "junior_moderator"):
        return True
    
    return False

async def create_event_storage(guild_id, event_name, event_type, duration_value, duration_unit, description, channel_id):
    """Create an event in MongoDB"""
    if db is None:
        return False
    
    guild_id = str(guild_id)
    
    # Calculate end time
    if duration_unit == "minutes":
        end_time = datetime.now() + timedelta(minutes=duration_value)
    elif duration_unit == "hours":
        end_time = datetime.now() + timedelta(hours=duration_value)
    elif duration_unit == "days":
        end_time = datetime.now() + timedelta(days=duration_value)
    
    event_data = {
        'guild_id': guild_id,
        'event_name': event_name.lower(),
        'event_type': event_type,
        'created_at': datetime.now(),
        'end_time': end_time,
        'description': description,
        'channel_id': str(channel_id),
        'participants': [],
        'winner': None,
        'winner_type': None
    }
    
    try:
        result = await db.events.insert_one(event_data)
        return result.inserted_id is not None
    except Exception as e:
        print(f"Error creating event: {e}")
        return False

async def get_event(guild_id, event_name):
    """Get event data from MongoDB"""
    if db is None:
        return None
    
    guild_id = str(guild_id)
    try:
        event = await db.events.find_one({
            'guild_id': guild_id,
            'event_name': event_name.lower()
        })
        return event
    except Exception as e:
        print(f"Error getting event: {e}")
        return None

async def check_event_exists(guild_id, event_name):
    """Check if event already exists in server"""
    event = await get_event(guild_id, event_name)
    return event is not None

@bot.tree.command(name="event-role", description="🎯 Set the event role")
@app_commands.describe(role="Role that can create/announce events")
async def event_role(interaction: discord.Interaction, role: discord.Role):
    """Set the event role - only server owner can use"""
    
    if interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("❌ Only server owner can set the event role!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    try:
        await update_server_data(interaction.guild.id, {'event_role': str(role.id)})
        
        embed = discord.Embed(
            title="✅ Event Role Updated",
            description=f"**Role:** {role.mention}\n**Permissions:** Can create and announce events",
            color=BrandColors.SUCCESS,
            timestamp=datetime.now()
        )
        embed.set_footer(text=BOT_FOOTER, icon_url=interaction.client.user.display_avatar.url)
        await interaction.followup.send(embed=embed)
        
        # Log action
        log_msg = f"🎯 [EVENT-ROLE] {interaction.user.mention} set event role to {role.mention}"
        await log_action(interaction.guild.id, "events", log_msg)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
        await log_action(interaction.guild.id, "error-log", f"⚠️ [EVENT-ROLE ERROR] {interaction.user}: {str(e)}")

@bot.tree.command(name="create-event", description="🎊 Create a new event")
@app_commands.describe(
    event_name="Name of the event (unique per server)",
    event_type="Type of event (giveaway, contest, raffle, etc)",
    duration_value="Duration value",
    duration_unit="Duration unit",
    description="Event description",
    channel="Channel to send event announcement"
)
@app_commands.choices(duration_unit=[
    app_commands.Choice(name="Minutes", value="minutes"),
    app_commands.Choice(name="Hours", value="hours"),
    app_commands.Choice(name="Days", value="days")
])
async def create_event(
    interaction: discord.Interaction,
    event_name: str,
    event_type: str,
    duration_value: int,
    duration_unit: str,
    description: str,
    channel: discord.TextChannel
):
    """Create a new event - Server owner, main moderator, junior moderator, or event role"""
    
    # Check permissions
    if interaction.user.id != interaction.guild.owner_id:
        if not await has_event_role_permission(interaction):
            await interaction.response.send_message("❌ You don't have permission to create events!", ephemeral=True)
            return
    
    await interaction.response.defer()
    
    try:
        # Check if event name already exists in server
        if await check_event_exists(interaction.guild.id, event_name):
            await interaction.followup.send(f"❌ Event name **{event_name}** already exists in this server!", ephemeral=True)
            return
        
        # Create event in database
        success = await create_event_storage(
            interaction.guild.id,
            event_name,
            event_type,
            duration_value,
            duration_unit,
            description,
            channel.id
        )
        
        if not success:
            await interaction.followup.send("❌ Failed to create event in database!", ephemeral=True)
            return
        
        # Calculate end time for display
        if duration_unit == "minutes":
            end_time = datetime.now() + timedelta(minutes=duration_value)
        elif duration_unit == "hours":
            end_time = datetime.now() + timedelta(hours=duration_value)
        else:
            end_time = datetime.now() + timedelta(days=duration_value)
        
        # Create announcement embed
        embed = discord.Embed(
            title=f"🎊 {event_name}",
            description=description,
            color=BrandColors.PRIMARY,
            timestamp=datetime.now()
        )
        embed.add_field(name="📋 Type", value=event_type, inline=True)
        embed.add_field(name="⏱️ Duration", value=f"{duration_value} {duration_unit}", inline=True)
        embed.add_field(name="⏰ Ends at", value=f"<t:{int(end_time.timestamp())}:f>", inline=False)
        embed.add_field(name="👥 Participants", value="0", inline=True)
        embed.add_field(name="📝 React to enter!", value=f"React with 👑 to participate in this {event_type}!", inline=False)
        embed.set_footer(text=f"{BOT_FOOTER} • Event ID: {event_name}", icon_url=interaction.client.user.display_avatar.url)
        
        # Send announcement
        event_msg = await channel.send(embed=embed)
        await event_msg.add_reaction("👑")
        
        # Update event with message ID
        if db is not None:
            await db.events.update_one(
                {'guild_id': str(interaction.guild.id), 'event_name': event_name.lower()},
                {'$set': {'message_id': str(event_msg.id), 'message_channel': str(channel.id)}}
            )
        
        # Send confirmation
        confirm_embed = discord.Embed(
            title="✅ Event Created",
            description=f"**Event:** {event_name}\n**Type:** {event_type}\n**Channel:** {channel.mention}",
            color=BrandColors.SUCCESS,
            timestamp=datetime.now()
        )
        confirm_embed.set_footer(text=BOT_FOOTER, icon_url=interaction.client.user.display_avatar.url)
        await interaction.followup.send(embed=confirm_embed)
        
        # Log action
        log_msg = f"🎊 [CREATE-EVENT] {interaction.user.mention} created event **{event_name}** ({event_type}) in {channel.mention}"
        await log_action(interaction.guild.id, "events", log_msg)
        
        # Log to global logging
        try:
            from advanced_logging import send_global_log
            global_log_msg = f"**🎊 Event Created**\n**Name:** {event_name}\n**Type:** {event_type}\n**User:** {interaction.user}\n**Channel:** {channel.name}\n**Duration:** {duration_value} {duration_unit}"
            await send_global_log("events", global_log_msg, interaction.guild)
        except:
            pass
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
        await log_action(interaction.guild.id, "error-log", f"⚠️ [CREATE-EVENT ERROR] {interaction.user}: {str(e)}")

@bot.tree.command(name="announce-winner", description="🏆 Announce event winner (random or custom)")
async def announce_winner(interaction: discord.Interaction):
    """Announce event winner - Server owner, main moderator, or junior moderator only"""
    
    # Check permissions - HIDDEN from help menu, only these users see it
    if interaction.user.id != interaction.guild.owner_id:
        if not await has_permission(interaction, "main_moderator"):
            # Don't show this command was attempted
            await interaction.response.send_message("This command doesn't exist or you don't have access.", ephemeral=True)
            return
    
    await interaction.response.send_modal(AnnounceWinnerModal())

class AnnounceWinnerModal(discord.ui.Modal, title="Announce Winner"):
    """Modal to select winner type"""
    event_name_input = discord.ui.TextInput(
        label="Event Name",
        placeholder="Enter the event name",
        required=True
    )
    winner_type_input = discord.ui.TextInput(
        label="Winner Type (random/custom)",
        placeholder="Type 'random' or 'custom'",
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        try:
            event_name = self.event_name_input.value
            winner_type = self.winner_type_input.value.lower()
            
            # Get event from database
            event = await get_event(interaction.guild.id, event_name)
            
            if not event:
                await interaction.followup.send(f"❌ Event **{event_name}** not found!", ephemeral=True)
                return
            
            if winner_type == "random":
                if not event.get('participants'):
                    await interaction.followup.send("❌ No participants in this event!", ephemeral=True)
                    return
                
                # Select random winner
                winner_id = random.choice(event['participants'])
                guild = bot.get_guild(int(event['guild_id']))
                winner = guild.get_member(winner_id)
                
                if not winner:
                    await interaction.followup.send("❌ Could not find winner member!", ephemeral=True)
                    return
                
                # Request other info
                await interaction.followup.send(
                    f"🏆 Selected winner: **{winner.mention}**\n\nPlease provide: channel, description, image_url",
                    ephemeral=True
                )
                
                # Store winner temporarily
                if db is not None:
                    await db.events.update_one(
                        {'_id': event['_id']},
                        {'$set': {'winner': winner_id, 'winner_type': 'random'}}
                    )
                
            elif winner_type == "custom":
                # Request winner details
                await interaction.followup.send(
                    f"🎯 Custom winner mode\n\nPlease provide: winner_name/id, channel, description, image_url",
                    ephemeral=True
                )
                
                if db is not None:
                    await db.events.update_one(
                        {'_id': event['_id']},
                        {'$set': {'winner_type': 'custom'}}
                    )
            else:
                await interaction.followup.send("❌ Invalid winner type! Use 'random' or 'custom'", ephemeral=True)
        
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

@bot.tree.command(name="announce-random-winner", description="🏆 Announce random winner from event")
@app_commands.describe(
    event_name="Name of the event",
    channel="Channel to announce winner",
    description="Winner announcement description",
    image_url="Image URL (optional)"
)
async def announce_random_winner(
    interaction: discord.Interaction,
    event_name: str,
    channel: discord.TextChannel,
    description: str,
    image_url: str = None
):
    """Announce random winner - Server owner, main moderator, junior moderator only"""
    
    if interaction.user.id != interaction.guild.owner_id:
        if not await has_permission(interaction, "main_moderator"):
            await interaction.response.send_message("❌ You don't have permission!", ephemeral=True)
            return
    
    await interaction.response.defer()
    
    try:
        event = await get_event(interaction.guild.id, event_name)
        
        if not event:
            await interaction.followup.send(f"❌ Event **{event_name}** not found!", ephemeral=True)
            return
        
        if not event.get('participants'):
            await interaction.followup.send("❌ No participants in this event!", ephemeral=True)
            return
        
        # Select random winner
        winner_id = random.choice(event['participants'])
        winner = interaction.guild.get_member(winner_id)
        
        if not winner:
            await interaction.followup.send("❌ Could not find winner member!", ephemeral=True)
            return
        
        # Create winner announcement
        embed = discord.Embed(
            title="🏆 Winner Announced!",
            description=description,
            color=BrandColors.PRIMARY,
            timestamp=datetime.now()
        )
        embed.add_field(name="🎉 Winner", value=f"{winner.mention}", inline=False)
        embed.add_field(name="📋 Event", value=event_name, inline=True)
        embed.add_field(name="👥 Total Participants", value=str(len(event['participants'])), inline=True)
        
        if image_url:
            embed.set_image(url=image_url)
        
        embed.set_footer(text=BOT_FOOTER, icon_url=interaction.client.user.display_avatar.url)
        
        # Send announcement
        await channel.send(embed=embed)
        
        # Update event
        if db is not None:
            await db.events.update_one(
                {'_id': event['_id']},
                {'$set': {'winner': winner_id, 'winner_type': 'random', 'announced': True}}
            )
        
        # Confirm
        confirm_embed = discord.Embed(
            title="✅ Winner Announced",
            description=f"**Winner:** {winner.mention}\n**Event:** {event_name}",
            color=BrandColors.SUCCESS,
            timestamp=datetime.now()
        )
        confirm_embed.set_footer(text=BOT_FOOTER, icon_url=interaction.client.user.display_avatar.url)
        await interaction.followup.send(embed=confirm_embed)
        
        # Log action
        log_msg = f"🏆 [RANDOM-WINNER] {interaction.user.mention} announced {winner.mention} as winner of **{event_name}** in {channel.mention}"
        await log_action(interaction.guild.id, "events", log_msg)
        
        # Log to global
        try:
            from advanced_logging import send_global_log
            global_log_msg = f"**🏆 Random Winner Announced**\n**Event:** {event_name}\n**Winner:** {winner}\n**Participants:** {len(event['participants'])}\n**Channel:** {channel.name}"
            await send_global_log("events", global_log_msg, interaction.guild)
        except:
            pass
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
        await log_action(interaction.guild.id, "error-log", f"⚠️ [RANDOM-WINNER ERROR] {interaction.user}: {str(e)}")

@bot.tree.command(name="announce-custom-winner", description="🎯 Announce custom winner")
@app_commands.describe(
    event_name="Name of the event",
    winner="Winner mention or name",
    channel="Channel to announce winner",
    description="Winner announcement description",
    image_url="Image URL (optional)"
)
async def announce_custom_winner(
    interaction: discord.Interaction,
    event_name: str,
    winner: discord.User,
    channel: discord.TextChannel,
    description: str,
    image_url: str = None
):
    """Announce custom winner - Server owner, main moderator, junior moderator only"""
    
    if interaction.user.id != interaction.guild.owner_id:
        if not await has_permission(interaction, "main_moderator"):
            await interaction.response.send_message("❌ You don't have permission!", ephemeral=True)
            return
    
    await interaction.response.defer()
    
    try:
        event = await get_event(interaction.guild.id, event_name)
        
        if not event:
            await interaction.followup.send(f"❌ Event **{event_name}** not found!", ephemeral=True)
            return
        
        # Create winner announcement
        embed = discord.Embed(
            title="🎯 Winner Announced!",
            description=description,
            color=BrandColors.PRIMARY,
            timestamp=datetime.now()
        )
        embed.add_field(name="🎉 Winner", value=f"{winner.mention}", inline=False)
        embed.add_field(name="📋 Event", value=event_name, inline=True)
        
        if image_url:
            embed.set_image(url=image_url)
        
        embed.set_footer(text=BOT_FOOTER, icon_url=interaction.client.user.display_avatar.url)
        
        # Send announcement
        await channel.send(embed=embed)
        
        # Update event
        if db is not None:
            await db.events.update_one(
                {'_id': event['_id']},
                {'$set': {'winner': winner.id, 'winner_type': 'custom', 'announced': True}}
            )
        
        # Confirm
        confirm_embed = discord.Embed(
            title="✅ Custom Winner Announced",
            description=f"**Winner:** {winner.mention}\n**Event:** {event_name}",
            color=BrandColors.SUCCESS,
            timestamp=datetime.now()
        )
        confirm_embed.set_footer(text=BOT_FOOTER, icon_url=interaction.client.user.display_avatar.url)
        await interaction.followup.send(embed=confirm_embed)
        
        # Log action
        log_msg = f"🎯 [CUSTOM-WINNER] {interaction.user.mention} announced {winner.mention} as custom winner of **{event_name}** in {channel.mention}"
        await log_action(interaction.guild.id, "events", log_msg)
        
        # Log to global
        try:
            from advanced_logging import send_global_log
            global_log_msg = f"**🎯 Custom Winner Announced**\n**Event:** {event_name}\n**Winner:** {winner}\n**Channel:** {channel.name}"
            await send_global_log("events", global_log_msg, interaction.guild)
        except:
            pass
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
        await log_action(interaction.guild.id, "error-log", f"⚠️ [CUSTOM-WINNER ERROR] {interaction.user}: {str(e)}")

# Add reaction listener for event participation
@bot.event
async def on_reaction_add(reaction, user):
    """Handle reaction to participate in events"""
    if user.bot:
        return
    
    if reaction.emoji != "👑":
        return
    
    try:
        # Check if this is an event message
        if db is None:
            return
        
        event = await db.events.find_one({
            'message_id': str(reaction.message.id),
            'message_channel': str(reaction.message.channel.id)
        })
        
        if not event:
            return
        
        # Add user to participants if not already there
        if user.id not in event.get('participants', []):
            await db.events.update_one(
                {'_id': event['_id']},
                {'$push': {'participants': user.id}}
            )
    except Exception as e:
        print(f"Error handling event reaction: {e}")

print("  ✓ /event-role command registered")
print("  ✓ /create-event command registered")
print("  ✓ /announce-random-winner command registered")
print("  ✓ /announce-custom-winner command registered (hidden from menu)")
print("✅ Event system loaded successfully with MongoDB persistence")
