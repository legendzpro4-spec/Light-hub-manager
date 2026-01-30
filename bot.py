import os
import discord
from discord.ext import commands
from discord import app_commands

# ---------------- CONFIG ----------------
INVITE_GOAL = 20
BOT_PREFIX = "."
TOKEN = os.getenv("DISCORD_TOKEN")
# ----------------------------------------

intents = discord.Intents.default()
intents.members = True  # Required to see members
intents.guilds = True

bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)

invite_cache = {}     # guild_id : list of invites
invite_counts = {}    # user_id : invite count
reward_roles = {}     # guild_id : role_id


# ---------------- BOT READY ----------------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

    for guild in bot.guilds:
        try:
            invite_cache[guild.id] = await guild.invites()
        except discord.Forbidden:
            print(f"❌ Missing permissions in {guild.name}")

    await bot.tree.sync()
    print("✅ Slash commands synced")


# ---------------- INVITE TRACKING ----------------
@bot.event
async def on_member_join(member):
    guild = member.guild

    if guild.id not in reward_roles:
        return

    old_invites = invite_cache.get(guild.id, [])
    new_invites = await guild.invites()

    inviter = None
    for new in new_invites:
        for old in old_invites:
            if new.code == old.code and new.uses > old.uses:
                inviter = new.inviter
                break

    invite_cache[guild.id] = new_invites

    if inviter is None:
        return

    invite_counts[inviter.id] = invite_counts.get(inviter.id, 0) + 1
    count = invite_counts[inviter.id]
    print(f"📨 {inviter} now has {count} invites")

    if count == INVITE_GOAL:
        role = guild.get_role(reward_roles[guild.id])
        if role:
            try:
                await inviter.add_roles(role)
                print(f"🎉 Gave {role.name} to {inviter}")
            except discord.Forbidden:
                print(f"❌ Role hierarchy issue for {inviter}")


# ---------------- /setrole COMMAND ----------------
@bot.tree.command(name="setrole", description="Set the reward role")
@app_commands.checks.has_permissions(administrator=True)
async def setrole(interaction: discord.Interaction, role: discord.Role):
    reward_roles[interaction.guild.id] = role.id
    await interaction.response.send_message(
        f"✅ Reward role set to **{role.name}**",
        ephemeral=True
    )


# ---------------- .r COMMAND (FIXED) ----------------
@bot.command()
@commands.has_permissions(manage_roles=True)
async def r(ctx, *, member: str = None):
    guild = ctx.guild

    if member is None:
        await ctx.send("❌ You must mention a user or provide their ID.")
        return

    # Convert mention or ID to member
    try:
        if member.startswith("<@") and member.endswith(">"):
            member_id = int(member.replace("<@", "").replace("!", "").replace(">", ""))
            member_obj = guild.get_member(member_id)
        else:
            member_id = int(member)
            member_obj = guild.get_member(member_id)
    except:
        await ctx.send("❌ Invalid member. Make sure you mention them or use their ID.")
        return

    if member_obj is None:
        await ctx.send("❌ Member not found in this server.")
        return

    if guild.id not in reward_roles:
        await ctx.send("❌ No reward role set. Use `/setrole` first.")
        return

    role = guild.get_role(reward_roles[guild.id])
    if role is None:
        await ctx.send("❌ The reward role no longer exists.")
        return

    if role in member_obj.roles:
        await ctx.send(f"⚠️ {member_obj.mention} already has **{role.name}**.")
        return

    try:
        await member_obj.add_roles(role, reason=f"Manual role by {ctx.author}")
        await ctx.send(f"✅ **Role added!** {member_obj.mention} has been given **{role.name}**")
        print(f"✅ Role {role.name} added to {member_obj} by {ctx.author}")
    except discord.Forbidden:
        await ctx.send(
            "❌ I can't add that role. Make sure my bot role is **above the reward role** and has Manage Roles permission."
        )
    except Exception as e:
        await ctx.send(f"❌ Unexpected error: `{e}`")


# ---------------- GLOBAL ERROR HANDLER ----------------
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Missing argument for the command.")
    else:
        await ctx.send(f"❌ An error occurred: `{error}`")


# ---------------- RUN BOT ----------------
if TOKEN is None:
    raise RuntimeError("DISCORD_TOKEN environment variable not set!")

bot.run(TOKEN)
