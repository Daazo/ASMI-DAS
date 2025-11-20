# RXT ENGINE Discord Bot

### Overview
RXT ENGINE is a multi-functional Discord bot designed for automation, moderation, and server management. It features a futuristic cyberpunk aesthetic, having been rebranded from its previous "VAAZHA" identity. The bot is fully operational and provides comprehensive server protection against various threats, including nuking, raiding, and permission abuse.

### User Preferences
- Professional futuristic cyberpunk aesthetic
- Clean, modern UI without emojis in code
- Consolidated branding through brand_config.py
- Economy features removed (focus on automation/moderation)

## Recent Changes

### November 20, 2025 - Phase 4: Anti-Alt, Auto Bot-Block, Malware Filter, Auto Warning System
- 🚫 **Anti-Alt System (New Account Quarantine)**
  - Automatically quarantines new accounts younger than configured days (default: 7 days)
  - Creates "🚫 Quarantine" role with view-only permissions
  - Sends DM to quarantined users explaining restrictions and when they'll be released
  - Logs all quarantine actions to security channel with account age details
  - Whitelist support via `/security-whitelist add anti_alt @user`
  - Configure minimum age via `/security-config feature:Anti-Alt min_age_days:X`
  
- 🤖 **Auto Bot-Block System**
  - Automatically blocks unauthorized bot joins to prevent raid bots
  - Kicks unauthorized bots immediately upon join
  - Whitelist support for authorized bots via `/security-whitelist add bot_block @bot`
  - Alerts sent to security channel when bots are blocked
  - Enable/disable via `/security-config feature:Auto Bot-Block enabled:True/False`
  
- 🛡️ **Malware/File Filter System**
  - Blocks 30+ dangerous file extensions (.exe, .bat, .cmd, .scr, .vbs, .jar, .msi, etc.)
  - Detects 13+ suspicious domains (grabify, iplogger, fake discord/steam, URL shorteners)
  - Automatically deletes messages containing malicious content
  - Auto-applies warning to violators via warning system
  - Whitelist support via `/security-whitelist add malware_filter @user`
  - Logs all blocked content to security channel
  - Enable/disable via `/security-config feature:Malware/File Filter enabled:True/False`
  
- ⚠️ **Auto Warning System (3-Strike Escalation)**
  - **Strike Level 1 (3 warnings)**: 1-hour timeout
  - **Strike Level 2 (5 warnings)**: 24-hour timeout
  - **Strike Level 3 (7 warnings)**: Permanent ban
  - Configurable strike thresholds via `/security-config feature:Auto Warning System strike_1:X strike_2:Y strike_3:Z`
  - All warnings persist in MongoDB database
  - DMs users on each warning with count and next strike level
  - Commands:
    - `/warn @user reason:"..."` - Issue manual warning
    - `/warnings @user` - View user's warning history
    - `/clearwarnings @user` - Clear all warnings for user
  - Warnings logged to moderation channel with full context
  - Automatic timeout/ban when strike thresholds exceeded

### November 20, 2025 - Phase 3: Anti-Nuke, Permission Shield, Webhook Protection Implementation
- 🚫 **Anti-Nuke System (Mass Action Detection & Auto-Rollback)**
  - **Mass Ban Detection & Rollback**: Tracks bans via audit logs (default: 5 bans/min), automatically unbans all affected users
  - **Mass Kick Detection & Re-Invite**: Detects kicks in `on_member_remove` via audit logs (default: 5 kicks/min), automatically DMs kicked users with re-invite links to rejoin the server (users with DMs disabled will need manual re-invitation)
  - **Mass Role Deletion & Rollback**: Monitors role deletes (default: 3 deletes/min), recreates deleted roles with full permissions
  - **Mass Channel Deletion & Rollback**: Monitors channel deletes (default: 3 deletes/min), recreates deleted channels with settings
  - **Independent Threshold Configuration**: Separate configurable thresholds for bans, kicks, role deletes, and channel deletes via `/security-config`
  - Automatically tracks destructive actions via Discord audit logs
  - Sends critical alerts to security channel when nuke detected
  - DMs server owner with critical alerts and moderator information
  - **Full Auto-Rollback System**:
    - Unbans: Automatically unbans all users when mass ban threshold exceeded
    - Kicks: Generates invite links and DMs them to kicked users (best-effort within Discord API constraints)
    - Roles: Recreates deleted roles with original permissions, colors, and settings
    - Channels: Recreates deleted text/voice channels with topics, slowmode, and categories
  - Rollback actions logged to security channel with success count
  - Protects against server nuking/raiding attacks with automatic mitigation
  
- 🛡️ **Permission Shield System**
  - Monitors role permission changes in real-time
  - Automatically reverts unauthorized dangerous permission additions:
    - Administrator, Manage Server, Manage Roles, Manage Channels
    - Ban Members, Kick Members, Manage Webhooks, Manage Guild
  - Main moderators are whitelisted to make permission changes
  - Sends alerts to security channel with moderator details
  - Works on Admin roles, Moderator roles, and @everyone role
  
- 🔗 **Webhook Protection System**
  - Monitors webhook creation and deletion events
  - Automatically deletes unauthorized webhooks
  - Main moderators are whitelisted to create webhooks
  - Sends alerts to security channel when unauthorized webhooks detected
  
- **Enhanced /security-config Command**
  - Added separate threshold configuration for each anti-nuke action type
  - Parameters: `ban_threshold`, `kick_threshold`, `role_threshold`, `channel_threshold`
  - Supports all Phase 1, 2, 3, and 4 security features
  - Individual enable/disable control for each feature

### System Architecture

**Core Components:**
- **main.py**: Entry point, event handlers, and help command system.
- **brand_config.py**: Centralized branding configuration (colors, constants, footer).
- **keep_alive.py**: Flask web server for bot uptime monitoring.

**Modular Design:**
The bot's functionalities are organized into distinct modules:
- **xp_commands.py**: Manages the XP/leveling system.
- **moderation_commands.py**: Provides moderation tools (ban, kick, mute, warn).
- **setup_commands.py**: Handles server configuration and setup.
- **communication_commands.py**: Facilitates announcements, messages, and DM tools.
- **ticket_commands.py**: Implements a support ticket system.
- **reaction_roles.py**: Manages reaction-based role assignments.
- **security_commands.py**: Contains anti-raid, anti-nuke, and verification features.

**Visual Systems:**
- **profile_cards.py**: Generates futuristic profile cards using PIL.
- **global_logging.py**: Centralized logging system for server events.

**UI/UX and Theming:**
- **RXT ENGINE Quantum Purple Theme**: Utilizes a consistent color scheme across all embeds and notifications.
- **Brand Colors**: Primary (#8A4FFF - Quantum Purple), Secondary (#4F8CFF - Hyper Blue), Accent (#00E68A - Neon Green), Warning (#FFD700 - Gold), Error (#FF4444 - Red), Background (#0A0A0F - Deep Space), Text (#E0E0E0 - Silver).
- **Consistent Branding**: All branding elements are centralized in `brand_config.py`.

**Key Features:**
- **Anti-Alt System**: Quarantines new accounts younger than configured days to prevent alt account abuse.
- **Auto Bot-Block**: Prevents unauthorized bot joins to protect against raid bots.
- **Malware/File Filter**: Blocks dangerous files and suspicious links with auto-warning system.
- **Auto Warning System**: 3-strike escalation system (3/5/7 warnings) with automatic timeout/ban enforcement.
- **Anti-Nuke System**: Detects and rolls back mass bans, kicks, role deletions, and channel deletions using audit logs with configurable thresholds.
- **Permission Shield**: Monitors and reverts unauthorized dangerous role permission changes to prevent privilege escalation.
- **Webhook Protection**: Automatically deletes unauthorized webhooks while allowing whitelisted moderators to create them.
- **Anti-Spam & Anti-Raid**: Detects and mitigates message spam and server raids through auto-timeout and auto-kick mechanisms.
- **Link Filter & Anti-Invite**: Blocks external links and Discord invite links, with whitelist support for trusted users and channels.
- **Enhanced Timeout System**: Applies timeouts with role removal, dedicated timeout channels, and automatic role restoration.
- **CAPTCHA Verification**: Secure, modal-based CAPTCHA challenge using PIL-generated images for user verification.
- **Whitelist Framework**: Feature-specific whitelists for users to bypass certain security restrictions.
- **Karma/XP System**: Community recognition and leveling system with custom rank cards.
- **Ticket System**: Comprehensive support ticket management.
- **Reaction Roles**: Role assignment through interactive reactions.
- **Global Logging**: Centralized logging for all significant server events.

**Architectural Decisions:**
- Centralized branding via `brand_config.py` for consistency.
- PIL image generation uses `BrandColorsRGB` for compatibility.
- Owner mentions are clickable using the `BOT_OWNER_ID` environment variable.
- Focus on a professional, modern, and futuristic theme.

### External Dependencies
- **discord.py**: Python API wrapper for Discord.
- **motor**: Asynchronous MongoDB driver for database interactions.
- **Pillow (PIL)**: Used for image generation, particularly for profile cards and CAPTCHAs.
- **Flask**: Utilized for the `keep_alive.py` web server to maintain bot uptime.
- **MongoDB**: Primary database for persistent storage, including server configurations, user data, tickets, logs, reaction roles, and warnings.