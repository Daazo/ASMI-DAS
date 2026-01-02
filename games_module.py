import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from datetime import datetime
from typing import Optional, Dict, List
import os

# Import core dependencies
from main import bot, db, get_server_data, update_server_data, log_action
from brand_config import (
    BrandColors, VisualElements, BOT_FOOTER, 
    create_success_embed, create_error_embed, create_info_embed
)

# Global match tracking to prevent multiple matches per user
active_matches: Dict[int, str] = {} # user_id -> game_name

async def log_game_event(guild: discord.Guild, user: discord.Member, game_name: str, action: str, channel: discord.TextChannel):
    """Log game events to global and per-server logs"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = (
        f"🎮 **[GAME EVENT]**\n"
        f"**Game:** {game_name}\n"
        f"**Action:** {action}\n"
        f"**Server:** {guild.name} ({guild.id})\n"
        f"**User:** {user.mention} ({user.id})\n"
        f"**Channel:** {channel.mention}\n"
        f"**Timestamp:** {timestamp}"
    )
    
    # 1. Per-server logs (auto-create #games-logs)
    try:
        log_channel = discord.utils.get(guild.text_channels, name="games-logs")
        if not log_channel:
            # Create channel if it doesn't exist
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            log_channel = await guild.create_text_channel("games-logs", overwrites=overwrites, reason="Auto-created for game logging")
        
        embed = discord.Embed(
            title=f"🎮 RXT GAME LOG • {game_name}",
            description=log_msg,
            color=BrandColors.PRIMARY,
            timestamp=datetime.now()
        )
        embed.set_footer(text=BOT_FOOTER)
        await log_channel.send(embed=embed)
    except Exception as e:
        print(f"Error in per-server game logging: {e}")

    # 2. Global Logging System
    try:
        from advanced_logging import send_global_log
        await send_global_log("general", log_msg, guild)
    except Exception as e:
        print(f"Error in global game logging: {e}")

class TicTacToeButton(discord.ui.Button['TicTacToeView']):
    def __init__(self, x: int, y: int):
        super().__init__(style=discord.ButtonStyle.secondary, label='\u200b', row=y)
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view = self.view
        state = view.board[self.y][self.x]
        
        if state != 0:
            return

        if interaction.user.id != view.current_player.id:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return

        if view.current_player == view.p1:
            self.style = discord.ButtonStyle.primary
            self.label = 'X'
            view.board[self.y][self.x] = 1
            view.current_player = view.p2
            content = f"It is now {view.p2.mention}'s turn (O)"
        else:
            self.style = discord.ButtonStyle.success
            self.label = 'O'
            view.board[self.y][self.x] = 2
            view.current_player = view.p1
            content = f"It is now {view.p1.mention}'s turn (X)"

        self.disabled = True
        winner = view.check_winner()
        
        if winner is not None:
            if winner == 1:
                content = f"🎉 **{view.p1.mention} (X) WON!**"
                await log_game_event(interaction.guild, view.p1, "Tic-Tac-Toe", "Victory", interaction.channel)
            elif winner == 2:
                content = f"🎉 **{view.p2.mention} (O) WON!**"
                await log_game_event(interaction.guild, view.p2, "Tic-Tac-Toe", "Victory", interaction.channel)
            else:
                content = "🤝 **It's a DRAW!**"
                await log_game_event(interaction.guild, view.p1, "Tic-Tac-Toe", "Draw", interaction.channel)

            for child in view.children:
                child.disabled = True
            view.stop()
            active_matches.pop(view.p1.id, None)
            active_matches.pop(view.p2.id, None)

        await interaction.response.edit_message(content=content, view=view)

class TicTacToeView(discord.ui.View):
    def __init__(self, p1: discord.Member, p2: discord.Member):
        super().__init__(timeout=60.0)
        self.p1 = p1
        self.p2 = p2
        self.current_player = p1
        self.board = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
        for y in range(3):
            for x in range(3):
                self.add_item(TicTacToeButton(x, y))

    def check_winner(self):
        for i in range(3):
            if self.board[i][0] == self.board[i][1] == self.board[i][2] != 0:
                return self.board[i][0]
            if self.board[0][i] == self.board[1][i] == self.board[2][i] != 0:
                return self.board[0][i]
        if self.board[0][0] == self.board[1][1] == self.board[2][2] != 0:
            return self.board[0][0]
        if self.board[0][2] == self.board[1][1] == self.board[2][0] != 0:
            return self.board[0][2]
        
        if all(cell != 0 for row in self.board for cell in row):
            return 0 # Draw
        return None

    async def on_timeout(self):
        active_matches.pop(self.p1.id, None)
        active_matches.pop(self.p2.id, None)

class RPSView(discord.ui.View):
    def __init__(self, p1: discord.Member, p2: discord.Member):
        super().__init__(timeout=60.0)
        self.p1 = p1
        self.p2 = p2
        self.choices = {p1.id: None, p2.id: None}

    async def process_rps(self, interaction: discord.Interaction):
        if all(self.choices.values()):
            c1, c2 = self.choices[self.p1.id], self.choices[self.p2.id]
            
            if c1 == c2:
                result = f"🤝 **DRAW!** Both chose {c1}."
                await log_game_event(interaction.guild, self.p1, "Rock Paper Scissors", "Draw", interaction.channel)
            elif (c1 == "Rock" and c2 == "Scissors") or (c1 == "Paper" and c2 == "Rock") or (c1 == "Scissors" and c2 == "Paper"):
                result = f"🎉 **{self.p1.mention} WON!** {c1} beats {c2}."
                await log_game_event(interaction.guild, self.p1, "Rock Paper Scissors", "Victory", interaction.channel)
            else:
                result = f"🎉 **{self.p2.mention} WON!** {c2} beats {c1}."
                await log_game_event(interaction.guild, self.p2, "Rock Paper Scissors", "Victory", interaction.channel)

            for child in self.children:
                child.disabled = True
            
            active_matches.pop(self.p1.id, None)
            active_matches.pop(self.p2.id, None)
            await interaction.message.edit(content=result, view=self)
            self.stop()

    @discord.ui.button(label="Rock", style=discord.ButtonStyle.primary, emoji="🪨")
    async def rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in self.choices:
            return await interaction.response.send_message("You are not in this game!", ephemeral=True)
        if self.choices[interaction.user.id]:
            return await interaction.response.send_message("You already chose!", ephemeral=True)
        
        self.choices[interaction.user.id] = "Rock"
        await interaction.response.send_message("You chose Rock!", ephemeral=True)
        await self.process_rps(interaction)

    @discord.ui.button(label="Paper", style=discord.ButtonStyle.success, emoji="📄")
    async def paper(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in self.choices:
            return await interaction.response.send_message("You are not in this game!", ephemeral=True)
        if self.choices[interaction.user.id]:
            return await interaction.response.send_message("You already chose!", ephemeral=True)
        
        self.choices[interaction.user.id] = "Paper"
        await interaction.response.send_message("You chose Paper!", ephemeral=True)
        await self.process_rps(interaction)

    @discord.ui.button(label="Scissors", style=discord.ButtonStyle.danger, emoji="✂️")
    async def scissors(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in self.choices:
            return await interaction.response.send_message("You are not in this game!", ephemeral=True)
        if self.choices[interaction.user.id]:
            return await interaction.response.send_message("You already chose!", ephemeral=True)
        
        self.choices[interaction.user.id] = "Scissors"
        await interaction.response.send_message("You chose Scissors!", ephemeral=True)
        await self.process_rps(interaction)

    async def on_timeout(self):
        active_matches.pop(self.p1.id, None)
        active_matches.pop(self.p2.id, None)

class GamesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="tictactoe", description="Start a Tic-Tac-Toe match")
    async def tictactoe(self, interaction: discord.Interaction, opponent: discord.Member):
        if opponent.bot or opponent == interaction.user:
            return await interaction.response.send_message("Invalid opponent!", ephemeral=True)
        
        server_data = await get_server_data(interaction.guild.id)
        game_channel_id = server_data.get("game_channel_tictactoe")
        
        if not game_channel_id or str(interaction.channel_id) != game_channel_id:
            channel_mention = f"<#{game_channel_id}>" if game_channel_id else "a designated channel"
            return await interaction.response.send_message(f"❌ This command can only be used in {channel_mention}.", ephemeral=True)

        if interaction.user.id in active_matches or opponent.id in active_matches:
            return await interaction.response.send_message("One of you is already in a match!", ephemeral=True)

        active_matches[interaction.user.id] = "tictactoe"
        active_matches[opponent.id] = "tictactoe"
        
        view = TicTacToeView(interaction.user, opponent)
        await interaction.response.send_message(f"⚔️ **Tic-Tac-Toe:** {interaction.user.mention} vs {opponent.mention}\nIt's {interaction.user.mention}'s turn (X)", view=view)
        await log_game_event(interaction.guild, interaction.user, "Tic-Tac-Toe", f"Started match against {opponent.name}", interaction.channel)

    @app_commands.command(name="rps", description="Start a Rock Paper Scissors match")
    async def rps(self, interaction: discord.Interaction, opponent: discord.Member):
        if opponent.bot or opponent == interaction.user:
            return await interaction.response.send_message("Invalid opponent!", ephemeral=True)

        server_data = await get_server_data(interaction.guild.id)
        game_channel_id = server_data.get("game_channel_rps")
        
        if not game_channel_id or str(interaction.channel_id) != game_channel_id:
            channel_mention = f"<#{game_channel_id}>" if game_channel_id else "a designated channel"
            return await interaction.response.send_message(f"❌ This command can only be used in {channel_mention}.", ephemeral=True)

        if interaction.user.id in active_matches or opponent.id in active_matches:
            return await interaction.response.send_message("One of you is already in a match!", ephemeral=True)

        active_matches[interaction.user.id] = "rps"
        active_matches[opponent.id] = "rps"
        
        view = RPSView(interaction.user, opponent)
        await interaction.response.send_message(f"⚔️ **Rock Paper Scissors:** {interaction.user.mention} vs {opponent.mention}\nChoose your move below!", view=view)
        await log_game_event(interaction.guild, interaction.user, "Rock Paper Scissors", f"Started match against {opponent.name}", interaction.channel)

class GameChannelCog(commands.GroupCog, name="game-channel"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="set", description="Set game channel for specific games")
    @app_commands.describe(game="Select game", channel="Target channel")
    @app_commands.choices(game=[
        app_commands.Choice(name="Tic-Tac-Toe", value="tictactoe"),
        app_commands.Choice(name="Rock Paper Scissors", value="rps")
    ])
    async def set_game_channel(self, interaction: discord.Interaction, game: app_commands.Choice[str], channel: discord.TextChannel):
        """Set the preferred channel for specific games"""
        # Import has_permission from main or re-implement check
        from main import has_permission
        if not await has_permission(interaction, "main_moderator") and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message(embed=create_error_embed("Access Denied", "Insufficient permissions."), ephemeral=True)

        field_name = f"game_channel_{game.value}"
        await update_server_data(interaction.guild.id, {field_name: str(channel.id)})
        
        await log_game_event(interaction.guild, interaction.user, game.name, f"Configured channel to {channel.name}", channel)
        await interaction.response.send_message(embed=create_success_embed("Configuration Updated", f"{game.name} channel set to {channel.mention}."), ephemeral=True)

async def setup_games(bot: commands.Bot):
    await bot.add_cog(GamesCog(bot))
    await bot.add_cog(GameChannelCog(bot))
