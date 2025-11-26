"""
Invite Tracker System - Tracks invites and logs new member joins
"""
import discord
from discord.ext import commands, tasks
from discord import app_commands
import motor.motor_asyncio
from datetime import datetime

# Brand configuration
from brand_config import BrandColors, BOT_FOOTER, VisualElements

# Global variables (set by main.py)
bot = None
db = None
get_server_data = None
update_server_data = None
log_action = None
has_permission = None
create_error_embed = None

def setup(bot_instance, db_instance, get_server_data_func, update_server_data_func, log_action_func, has_permission_func, create_error_embed_func):
    """Setup function called from main.py"""
    global bot, db, get_server_data, update_server_data, log_action, has_permission, create_error_embed
    bot = bot_instance
    db = db_instance
    get_server_data = get_server_data_func
    update_server_data = update_server_data_func
    log_action = log_action_func
    has_permission = has_permission_func
    create_error_embed = create_error_embed_func
    
    # Start background task
    if not track_all_invites.is_running():
        track_all_invites.start()

async def get_invite_tracker(guild_id):
    """Get invite tracker config for server"""
    guild_id = str(guild_id)
    if db is not None:
        server_data = await get_server_data(guild_id)
        return server_data.get('invite_tracker', {})
    return {}

async def set_invite_tracker(guild_id, config):
    """Save invite tracker config"""
    guild_id = str(guild_id)
    if db is not None:
        await update_server_data(guild_id, {'invite_tracker': config})

@tasks.loop(minutes=1)
async def track_all_invites():
    """Background task to periodically save invite counts"""
    if db is None or bot is None:
        return
    
    try:
        for guild in bot.guilds:
            try:
                invites = await guild.invites()
                guild_id = str(guild.id)
                
                await db.invite_data.update_one(
                    {'guild_id': guild_id},
                    {'$set': {
                        'invites': {inv.code: {'uses': inv.uses, 'inviter_id': inv.inviter.id if inv.inviter else None} for inv in invites},
                        'updated_at': datetime.utcnow()
                    }},
                    upsert=True
                )
            except Exception as e:
                pass
    except Exception as e:
        pass

@track_all_invites.before_loop
async def before_track_invites():
    """Wait until bot is ready"""
    await bot.wait_until_ready()

async def get_previous_invites(guild_id):
    """Get previous invite data"""
    guild_id = str(guild_id)
    if db is not None:
        data = await db.invite_data.find_one({'guild_id': guild_id})
        return data.get('invites', {}) if data else {}
    return {}

async def find_inviter(guild_id, before_invites):
    """Find who invited the new member"""
    try:
        guild = bot.get_guild(int(guild_id))
        if not guild:
            return None, None
        
        current_invites = await guild.invites()
        
        # Find which invite was used (increased uses count)
        for invite in current_invites:
            prev = before_invites.get(invite.code, {})
            prev_uses = prev.get('uses', 0) if prev else 0
            
            # If uses increased, this invite was used
            if invite.uses > prev_uses:
                if invite.inviter:
                    return invite.inviter, invite
        
        # If no inviter found, try to return any inviter
        for invite in current_invites:
            if invite.inviter and invite.uses > 0:
                return invite.inviter, invite
        
        return None, None
    except Exception as e:
        print(f"❌ [INVITE TRACKER] Failed to find inviter: {e}")
        return None, None

async def render_tracker_message(member, inviter, invite_count, tracker_config):
    """Render the invite tracker message with variables"""
    try:
        title = tracker_config.get('title', 'New Member Joined')
        description = tracker_config.get('description', 'Welcome {user}!')
        image_url = tracker_config.get('image_url', '')
        
        # Replace variables
        description = description.replace('{user}', member.mention)
        if inviter:
            description = description.replace('{inviter}', inviter.mention)
            description = description.replace('{invite_count}', str(invite_count))
        else:
            description = description.replace('{inviter}', 'Unknown')
            description = description.replace('{invite_count}', '0')
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=BrandColors.SUCCESS,
            timestamp=datetime.utcnow()
        )
        
        if image_url:
            embed.set_image(url=image_url)
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Member", value=member.mention, inline=True)
        
        if inviter:
            embed.add_field(name="Invited By", value=inviter.mention, inline=True)
            embed.add_field(name="Total Invites", value=str(invite_count), inline=True)
        else:
            embed.add_field(name="Invited By", value="Unknown", inline=True)
            embed.add_field(name="Total Invites", value="0", inline=True)
        
        embed.set_footer(text=BOT_FOOTER)
        
        return embed
    except Exception as e:
        print(f"❌ [INVITE TRACKER] Failed to render message: {e}")
        return None

async def check_rejoin(guild_id, member_id):
    """Check if user rejoined"""
    guild_id = str(guild_id)
    member_id = str(member_id)
    
    if db is not None:
        try:
            rejoin_data = await db.member_rejoin.find_one({'guild_id': guild_id, 'member_id': member_id})
            return rejoin_data is not None
        except:
            return False
    return False

async def record_member_join(guild_id, member_id):
    """Record member join"""
    guild_id = str(guild_id)
    member_id = str(member_id)
    
    if db is not None:
        try:
            await db.member_rejoin.update_one(
                {'guild_id': guild_id, 'member_id': member_id},
                {'$set': {'timestamp': datetime.utcnow()}},
                upsert=True
            )
        except Exception as e:
            print(f"❌ [INVITE TRACKER] Failed to record join: {e}")

# Command
class InviteTrackerCog(commands.Cog):
    def __init__(self, bot_instance):
        self.bot = bot_instance
    
    @app_commands.command(name="invite-tracker", description="Setup invite tracker")
    @app_commands.describe(
        title="Embed title",
        description="Embed description (use {user}, {inviter}, {invite_count})",
        channel="Channel to send tracker to",
        image_url="Image URL (optional)"
    )
    async def invite_tracker(self, interaction: discord.Interaction, title: str, description: str, channel: discord.TextChannel, image_url: str = ""):
        """Setup invite tracker for server"""
        # Permission check - Main Moderator OR Server Owner
        is_main_mod = await has_permission(interaction, "main_moderator")
        is_owner = interaction.user.id == interaction.guild.owner_id
        
        if not (is_main_mod or is_owner):
            await interaction.response.send_message(
                embed=create_error_embed("You need Main Moderator or Server Owner permission"),
                ephemeral=True
            )
            return
        
        try:
            # Validate channel exists and is accessible
            if not channel:
                await interaction.response.send_message(
                    embed=create_error_embed("Invalid channel provided"),
                    ephemeral=True
                )
                return
            
            # Save config
            config = {
                'enabled': True,
                'title': title,
                'description': description,
                'channel_id': channel.id,
                'image_url': image_url,
                'created_at': datetime.utcnow(),
                'created_by': str(interaction.user.id)
            }
            
            await set_invite_tracker(interaction.guild.id, config)
            
            # Confirm embed
            confirm_embed = discord.Embed(
                title="✅ Invite Tracker Setup",
                description=f"Invite tracker configured for {channel.mention}",
                color=BrandColors.SUCCESS
            )
            confirm_embed.add_field(name="Title", value=title, inline=False)
            confirm_embed.add_field(name="Description", value=description, inline=False)
            if image_url:
                confirm_embed.add_field(name="Image URL", value=image_url, inline=False)
            confirm_embed.set_footer(text=BOT_FOOTER)
            
            await interaction.response.send_message(embed=confirm_embed, ephemeral=True)
            
            # Log action
            await log_action(interaction.guild.id, "setup", f"📊 [INVITE TRACKER] Tracker configured by {interaction.user} for {channel.mention}")
            
        except Exception as e:
            print(f"❌ [INVITE TRACKER] Command error: {e}")
            await interaction.response.send_message(
                embed=create_error_embed(f"Error: {str(e)}"),
                ephemeral=True
            )

async def setup_cog(bot_instance):
    """Add cog to bot"""
    await bot_instance.add_cog(InviteTrackerCog(bot_instance))
