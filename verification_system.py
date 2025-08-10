
import discord
from discord.ext import commands
from discord import app_commands
from main import bot, has_permission, get_server_data, update_server_data, log_action
import asyncio
import random

# Default quiz questions
DEFAULT_QUESTIONS = [
    {
        "question": "Are you a human? (yes/no)",
        "answers": ["yes", "y", "human", "yeah", "yep"],
        "type": "text"
    },
    {
        "question": "What is 2 + 2?",
        "answers": ["4", "four"],
        "type": "text"
    },
    {
        "question": "Complete this sentence: The sky is ___",
        "answers": ["blue", "blue colored", "light blue"],
        "type": "text"
    }
]

@bot.tree.command(name="setupverification", description="🛡️ Setup join verification quiz")
@app_commands.describe(
    enabled="Enable or disable verification",
    verification_role="Role to give after successful verification",
    questions_count="Number of questions (1-3)"
)
async def setup_verification(
    interaction: discord.Interaction, 
    enabled: bool, 
    verification_role: discord.Role = None,
    questions_count: int = 2
):
    if not await has_permission(interaction, "main_moderator"):
        await interaction.response.send_message("❌ You need Main Moderator permissions to use this command!", ephemeral=True)
        return
    
    if questions_count < 1 or questions_count > 3:
        await interaction.response.send_message("❌ Questions count must be between 1 and 3!", ephemeral=True)
        return
    
    verification_settings = {
        'verification_enabled': enabled,
        'verification_role': str(verification_role.id) if verification_role else None,
        'verification_questions_count': questions_count
    }
    
    await update_server_data(interaction.guild.id, verification_settings)
    
    if enabled:
        embed = discord.Embed(
            title="🛡️ Verification System Enabled",
            description=f"**Status:** Enabled\n**Role:** {verification_role.mention if verification_role else 'None'}\n**Questions:** {questions_count}",
            color=0x43b581
        )
        embed.add_field(
            name="ℹ️ How It Works",
            value="New members will receive a DM with quiz questions. They must answer correctly to get access to the server.",
            inline=False
        )
    else:
        embed = discord.Embed(
            title="🛡️ Verification System Disabled",
            description="New members will no longer receive verification quizzes.",
            color=0xe74c3c
        )
    
    embed.set_footer(text="ᴠᴀᴀᴢʜᴀ")
    await interaction.response.send_message(embed=embed)
    
    await log_action(interaction.guild.id, "setup", f"🛡️ [VERIFICATION] {'Enabled' if enabled else 'Disabled'} by {interaction.user}")

async def send_verification_quiz(member):
    """Send verification quiz to new member"""
    server_data = await get_server_data(member.guild.id)
    
    if not server_data.get('verification_enabled'):
        return
    
    questions_count = server_data.get('verification_questions_count', 2)
    verification_role_id = server_data.get('verification_role')
    
    try:
        # Select random questions
        selected_questions = random.sample(DEFAULT_QUESTIONS, min(questions_count, len(DEFAULT_QUESTIONS)))
        
        embed = discord.Embed(
            title="🛡️ Server Verification Required",
            description=f"Welcome to **{member.guild.name}**!\n\nTo prevent spam and bot raids, please answer the following questions to gain access:",
            color=0x3498db
        )
        embed.set_footer(text="You have 5 minutes to complete this quiz.")
        
        await member.send(embed=embed)
        
        correct_answers = 0
        
        for i, q in enumerate(selected_questions, 1):
            question_embed = discord.Embed(
                title=f"Question {i}/{len(selected_questions)}",
                description=q["question"],
                color=0xf39c12
            )
            await member.send(embed=question_embed)
            
            def check(m):
                return m.author == member and isinstance(m.channel, discord.DMChannel)
            
            try:
                answer = await bot.wait_for('message', check=check, timeout=300.0)
                
                if answer.content.lower().strip() in q["answers"]:
                    correct_answers += 1
                    await member.send("✅ Correct!")
                else:
                    await member.send("❌ Incorrect answer.")
            
            except asyncio.TimeoutError:
                timeout_embed = discord.Embed(
                    title="⏰ Verification Timeout",
                    description="You took too long to answer. Please ask a moderator for manual verification.",
                    color=0xe74c3c
                )
                await member.send(embed=timeout_embed)
                return
        
        # Check if passed
        required_correct = len(selected_questions)
        
        if correct_answers >= required_correct:
            # Passed verification
            if verification_role_id:
                role = member.guild.get_role(int(verification_role_id))
                if role:
                    await member.add_roles(role, reason="Passed verification quiz")
            
            success_embed = discord.Embed(
                title="🎉 Verification Successful!",
                description=f"Congratulations! You've successfully verified your account and gained access to **{member.guild.name}**.\n\nWelcome to the community!",
                color=0x43b581
            )
            await member.send(embed=success_embed)
            
            await log_action(member.guild.id, "moderation", f"🛡️ [VERIFICATION] {member} passed verification quiz")
        
        else:
            # Failed verification
            failed_embed = discord.Embed(
                title="❌ Verification Failed",
                description=f"You answered {correct_answers}/{len(selected_questions)} questions correctly.\n\nPlease contact a moderator for manual verification.",
                color=0xe74c3c
            )
            await member.send(embed=failed_embed)
            
            await log_action(member.guild.id, "moderation", f"🛡️ [VERIFICATION] {member} failed verification quiz ({correct_answers}/{len(selected_questions)})")
    
    except discord.Forbidden:
        # User has DMs disabled - log for manual verification
        await log_action(member.guild.id, "moderation", f"🛡️ [VERIFICATION] {member} has DMs disabled - manual verification needed")
