import discord
from discord.ext import commands
from discord import app_commands
from main import bot
from brand_config import create_permission_denied_embed, create_owner_only_embed,  BOT_FOOTER, BrandColors, create_success_embed, create_error_embed, create_info_embed, create_command_embed, create_warning_embed
from main import has_permission, get_server_data, update_server_data, log_action
from captcha_generator import CaptchaGenerator

# CAPTCHA tracking data
security_data = {
    'captcha_data': {}  # Store active CAPTCHA challenges {user_id: captcha_text}
}

# Initialize CAPTCHA generator
captcha_gen = CaptchaGenerator()

# ═══════════════════════════════════════════════════════════════════════════
# CAPTCHA VERIFICATION SYSTEM
# ═══════════════════════════════════════════════════════════════════════════

# Verification type choices
class VerificationType:
    CAPTCHA = "captcha"
    BUTTON = "button"

# Verification setup command
@bot.tree.command(name="verification-setup", description="✅ Setup verification system for new members")
@app_commands.describe(
    channel="Channel where verification button will be posted",
    verified_role="Role to give verified members",
    verification_type="Type of verification: captcha (solve image) or button (one-click)",
    message="Custom verification message",
    remove_role="Role to remove from user when they verify (optional)"
)
@app_commands.choices(verification_type=[
    app_commands.Choice(name="🔐 CAPTCHA Verification (Solve image code)", value="captcha"),
    app_commands.Choice(name="✅ Button Verification (One-click verify)", value="button")
])
async def verification_setup(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    verified_role: discord.Role,
    verification_type: str = "captcha",
    message: str = "Click the button below to verify and gain access to the server!",
    remove_role: discord.Role = None
):
    if not await has_permission(interaction, "main_moderator"):
        await interaction.response.send_message(embed=create_permission_denied_embed("Main Moderator"), ephemeral=True)
        return

    # Update security settings
    server_data = await get_server_data(interaction.guild.id)
    security_settings = server_data.get('security_settings', {})
    verification_config = {
        'enabled': True,
        'verified_role': str(verified_role.id),
        'channel': str(channel.id),
        'verification_type': verification_type
    }
    if remove_role:
        verification_config['remove_role'] = str(remove_role.id)
    
    security_settings['verification_system'] = verification_config
    await update_server_data(interaction.guild.id, {'security_settings': security_settings})

    # Create verification embed based on type
    if verification_type == "button":
        embed = discord.Embed(
            title="🔐 **Server Verification Required**",
            description=f"**{message}**\n⚡ **Quantum Security Protocol Active**\n\n◆ **What verification grants you:**\n• Full server channel access\n• Participation in community\n• Complete member privileges\n\n✅ Click the button below to verify",
            color=BrandColors.PRIMARY
        )
    else:
        embed = discord.Embed(
            title="🔐 **Server Verification Required**",
            description=f"**{message}**\n⚡ **Quantum Security Protocol Active**\n\n◆ **What verification grants you:**\n• Full server channel access\n• Participation in community\n• Complete member privileges\n\n🔒 Complete CAPTCHA to verify",
            color=BrandColors.PRIMARY
        )
    embed.set_footer(text=BOT_FOOTER, icon_url=bot.user.display_avatar.url)

    view = VerificationView()  # Database-driven verification
    await channel.send(embed=embed, view=view)

    type_display = "🔐 CAPTCHA Verification" if verification_type == "captcha" else "✅ Button Verification"
    description = f"**Channel:** {channel.mention}\n**Verified Role:** {verified_role.mention}\n**Verification Type:** {type_display}"
    if remove_role:
        description += f"\n**Remove Role:** {remove_role.mention}"
    description += f"\n**Status:** Active\n\n*New members will need to verify before accessing the server.*"
    
    response_embed = discord.Embed(
        title="⚡ **Verification System Setup Complete**",
        description=description,
        color=BrandColors.PRIMARY
    )
    await interaction.response.send_message(embed=response_embed)
    await log_action(interaction.guild.id, "security", f"✅ [VERIFICATION] Verification system setup by {interaction.user} (Type: {verification_type})")

class CaptchaModal(discord.ui.Modal, title='🔐 CAPTCHA Verification'):
    """Modal for CAPTCHA input"""
    captcha_input = discord.ui.TextInput(
        label='Enter the CAPTCHA code shown in the image',
        placeholder='Type the 6-character code here...',
        required=True,
        max_length=6,
        min_length=6
    )
    
    def __init__(self, correct_captcha, verified_role, remove_role=None):
        super().__init__()
        self.correct_captcha = correct_captcha
        self.verified_role = verified_role
        self.remove_role = remove_role
    
    async def on_submit(self, interaction: discord.Interaction):
        user_input = self.captcha_input.value.upper().strip()
        
        # Remove user's CAPTCHA from cache
        user_id = str(interaction.user.id)
        if user_id in security_data['captcha_data']:
            del security_data['captcha_data'][user_id]
        
        if user_input == self.correct_captcha:
            # Correct CAPTCHA - verify the user
            try:
                # Remove the specified role if configured
                if self.remove_role and self.remove_role in interaction.user.roles:
                    await interaction.user.remove_roles(self.remove_role, reason="Role removed during verification")

                # Add verified role
                await interaction.user.add_roles(self.verified_role, reason="CAPTCHA verification successful")

                embed = discord.Embed(
                    title="⚡ **Verification Successful!**",
                    description="**Welcome to the server!**\n\n✓ CAPTCHA solved correctly\n✓ Quantum security check passed\n✓ Full server access granted\n\n◆ You are now a verified member!",
                    color=BrandColors.PRIMARY
                )
                embed.set_footer(text=BOT_FOOTER, icon_url=bot.user.display_avatar.url)
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                await log_action(interaction.guild.id, "security", f"✅ [CAPTCHA VERIFICATION] {interaction.user} verified successfully")

            except discord.Forbidden:
                await interaction.response.send_message(embed=create_error_embed("I don't have permission to assign the verified role. Contact administrators."), ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(embed=create_error_embed(f"Verification failed: {str(e)}"), ephemeral=True)
        else:
            # Incorrect CAPTCHA - RXT ENGINE Theme
            embed = discord.Embed(
                title="✗ **Verification Failed**",
                description=f"**◆ Incorrect CAPTCHA code**\n**You entered:** `{user_input}`\n\n⚡ Click the **Verify Me** button to get a new CAPTCHA\n💠 Each attempt generates a unique code",
                color=BrandColors.DANGER
            )
            embed.set_footer(text="◆ Quantum security active", icon_url=bot.user.display_avatar.url)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            await log_action(interaction.guild.id, "security", f"❌ [CAPTCHA FAILED] {interaction.user} entered incorrect CAPTCHA: {user_input}")

class VerificationView(discord.ui.View):
    def __init__(self, verified_role_id=None, remove_role_id=None):
        super().__init__(timeout=None)
        self.verified_role_id = verified_role_id
        self.remove_role_id = remove_role_id

    @discord.ui.button(label='✅ Verify Me', style=discord.ButtonStyle.success, emoji='✅', custom_id='verify_member')
    async def verify_member(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Get verification settings from database
        server_data = await get_server_data(interaction.guild.id)
        security_settings = server_data.get('security_settings', {})
        verification_config = security_settings.get('verification_system', {})

        if not verification_config.get('enabled', False):
            await interaction.response.send_message(embed=create_error_embed("Verification system is not enabled! Contact administrators."), ephemeral=True)
            return

        verified_role_id = verification_config.get('verified_role')
        remove_role_id = verification_config.get('remove_role')
        verification_type = verification_config.get('verification_type', 'captcha')

        if not verified_role_id:
            await interaction.response.send_message(embed=create_error_embed("Verification role not configured! Contact administrators."), ephemeral=True)
            return

        verified_role = interaction.guild.get_role(int(verified_role_id))
        if not verified_role:
            await interaction.response.send_message(embed=create_error_embed("Verification role not found! Contact administrators."), ephemeral=True)
            return

        if verified_role in interaction.user.roles:
            await interaction.response.send_message("✅ You are already verified!", ephemeral=True)
            return

        remove_role = None
        if remove_role_id:
            remove_role = interaction.guild.get_role(int(remove_role_id))

        # Handle Button Verification (one-click)
        if verification_type == "button":
            try:
                # Remove the specified role if configured
                if remove_role and remove_role in interaction.user.roles:
                    await interaction.user.remove_roles(remove_role, reason="Role removed during button verification")

                # Add verified role
                await interaction.user.add_roles(verified_role, reason="Button verification successful")

                embed = discord.Embed(
                    title="⚡ **Verification Successful!**",
                    description="**Welcome to the server!**\n\n✓ Button verification completed\n✓ Quantum security check passed\n✓ Full server access granted\n\n◆ You are now a verified member!",
                    color=BrandColors.PRIMARY
                )
                embed.set_footer(text=BOT_FOOTER, icon_url=bot.user.display_avatar.url)
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                await log_action(interaction.guild.id, "security", f"✅ [BUTTON VERIFICATION] {interaction.user} verified successfully")
                
                # Global logging for button verification
                try:
                    from advanced_logging import send_global_log
                    await send_global_log(
                        "security",
                        f"**✅ Button Verification**\n**User:** {interaction.user.mention}\n**Server:** {interaction.guild.name}",
                        interaction.guild
                    )
                except:
                    pass

            except discord.Forbidden:
                await interaction.response.send_message(embed=create_error_embed("I don't have permission to assign the verified role. Contact administrators."), ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(embed=create_error_embed(f"Verification failed: {str(e)}"), ephemeral=True)
            return

        # Handle CAPTCHA Verification
        try:
            # Generate unique CAPTCHA for this user
            captcha_text, captcha_file = captcha_gen.generate()

            # Store CAPTCHA for validation
            user_id = str(interaction.user.id)
            security_data['captcha_data'][user_id] = captcha_text

            # Create modal and view
            modal = CaptchaModal(captcha_text, verified_role, remove_role)

            # Send CAPTCHA image with button in ONE message - RXT ENGINE Theme
            embed = discord.Embed(
                title="🔐 **Quantum Security Verification**",
                description="**◆ Solve the CAPTCHA to verify:**\n\n**1.** Analyze the code in the image below\n**2.** Click the button to enter the code\n\n⚡ Code is case-insensitive\n💠 Quantum encryption active",
                color=BrandColors.PRIMARY
            )
            embed.set_image(url="attachment://captcha.png")
            embed.set_footer(text="◆ This CAPTCHA is uniquely generated for you", icon_url=bot.user.display_avatar.url)

            await interaction.response.send_message(
                embed=embed,
                file=captcha_file,
                view=CaptchaInputView(modal),
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(embed=create_error_embed(f"CAPTCHA generation failed: {str(e)}"), ephemeral=True)

class CaptchaInputView(discord.ui.View):
    """View with button to open CAPTCHA input modal"""
    def __init__(self, modal=None):
        super().__init__(timeout=None)  # Make it persistent
        self.modal = modal
    
    @discord.ui.button(label='Enter CAPTCHA Code', style=discord.ButtonStyle.success, emoji='✍️', custom_id='captcha_open_modal')
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.modal:
            await interaction.response.send_modal(self.modal)
        else:
            # Reconstruct modal if it's a persistent view from a restart
            server_data = await get_server_data(interaction.guild.id)
            security_settings = server_data.get('security_settings', {})
            verification_config = security_settings.get('verification_system', {})
            
            verified_role_id = verification_config.get('verified_role')
            remove_role_id = verification_config.get('remove_role')
            
            user_id = str(interaction.user.id)
            correct_captcha = security_data['captcha_data'].get(user_id)
            
            if not correct_captcha:
                await interaction.response.send_message("❌ Your CAPTCHA session has expired. Please click 'Verify Me' again.", ephemeral=True)
                return
                
            verified_role = interaction.guild.get_role(int(verified_role_id))
            remove_role = interaction.guild.get_role(int(remove_role_id)) if remove_role_id else None
            
            modal = CaptchaModal(correct_captcha, verified_role, remove_role)
            await interaction.response.send_modal(modal)
