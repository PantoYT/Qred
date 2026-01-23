import discord
from discord.ext import commands
from dotenv import load_dotenv
import json
import os
from datetime import datetime
import pathlib
import hashlib

# -------------------------------
# Load environment
# -------------------------------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

# JSON path in same folder as script
QUOTE_FILE = pathlib.Path(__file__).parent / "quotes.json"

# -------------------------------
# Discord bot setup
# -------------------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# -------------------------------
# Helper functions
# -------------------------------
def load_quotes():
    if QUOTE_FILE.exists():
        try:
            with open(QUOTE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error loading quotes: {e}")
            return []
    return []

def save_quotes(quotes):
    try:
        with open(QUOTE_FILE, "w", encoding="utf-8") as f:
            json.dump(quotes, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving quotes: {e}")

def format_author_name(name):
    return name.strip()

def categorize_author(count):
    if count <= 5:
        return "Początkujący filozof"
    elif count <= 15:
        return "Sokrates"
    elif count <= 30:
        return "Platon"
    elif count <= 50:
        return "Arystoteles"
    elif count <= 75:
        return "Konfucjusz"
    elif count <= 100:
        return "Seneka"
    else:
        return "Marcus Aurelius"

def get_daily_quote_index(quotes):
    if not quotes:
        return 0
    
    today = datetime.now().strftime("%Y-%m-%d")
    hash_obj = hashlib.md5(today.encode())
    hash_int = int(hash_obj.hexdigest(), 16)
    
    return hash_int % len(quotes)

# -------------------------------
# Events
# -------------------------------
@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="Tracking your quotes | /commands"
        )
    )

# -------------------------------
# Commands
# -------------------------------
@bot.tree.command(name="commands", description="Show all available commands")
async def commands_slash(interaction: discord.Interaction):
    embed = discord.Embed(title="Qred - Quote Tracker", description="Track your best Quotes.", color=0x1E3A8A)
    embed.add_field(name="/showrandom", value="Display a random quote", inline=False)
    embed.add_field(name="/addquote", value="Turns the last message into a quote", inline=False)
    embed.add_field(name="/createquote", value="Add a new quote manually", inline=False)
    embed.add_field(name="/displayquotes", value="Show all quotes (owner only)", inline=False)
    embed.add_field(name="/showauthors", value="Show all authors with number of quotes", inline=False)
    embed.add_field(name="/show {author}", value="Show quotes from specific author", inline=False)
    embed.add_field(name="/dailyquote", value="Show today's quote", inline=False)
    embed.add_field(name="/shutdown", value="Shut down the bot (owner only)", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="addquote", description="Turns the last message on the server into a quote")
async def addquote_slash(interaction: discord.Interaction):
    await interaction.response.defer()
    
    quotes = load_quotes()
    
    messages = [msg async for msg in interaction.channel.history(limit=20)]
    last_msg = None
    for msg in messages:
        if not msg.author.bot:
            last_msg = msg
            break
    
    if not last_msg:
        await interaction.followup.send("No suitable message found in recent history.")
        return
    
    if not last_msg.content.strip():
        await interaction.followup.send("Cannot add empty message as quote.")
        return
    
    if len(last_msg.content) > 500:
        await interaction.followup.send("Message too long (max 500 characters).")
        return
    
    author_name = last_msg.author.name
    date_str = datetime.now().strftime("%d/%m/%Y")
    
    new_quote = {
        "text": last_msg.content.strip(),
        "author": author_name,
        "date": date_str
    }
    
    quotes.append(new_quote)
    save_quotes(quotes)
    
    await interaction.followup.send(f'Quote added from last message: "{last_msg.content}" - {author_name} ({date_str})')

@bot.tree.command(name="createquote", description="Add a new quote manually")
async def createquote_slash(interaction: discord.Interaction, quote: str, author: str = None):
    if not quote.strip():
        await interaction.response.send_message("Quote cannot be empty.", ephemeral=True)
        return
    
    if len(quote) > 500:
        await interaction.response.send_message("Quote too long (max 500 characters).", ephemeral=True)
        return
    
    quotes = load_quotes()
    
    author_name = format_author_name(author) if author else interaction.user.name
    date_str = datetime.now().strftime("%d/%m/%Y")
    
    new_quote = {
        "text": quote.strip(),
        "author": author_name,
        "date": date_str
    }
    
    quotes.append(new_quote)
    save_quotes(quotes)
    
    await interaction.response.send_message(f'Quote added: "{quote}" - {author_name} ({date_str})')

@bot.tree.command(name="displayquotes", description="Show all quotes (owner only)")
async def displayquotes_slash(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("Owner-only command.", ephemeral=True)
        return
    
    quotes = load_quotes()
    
    if not quotes:
        await interaction.response.send_message("No quotes to display.")
        return
    
    embeds = []
    current_embed = discord.Embed(title="All Quotes", color=0x1E3A8A)
    field_count = 0
    
    for q in quotes:
        if field_count >= 25:
            embeds.append(current_embed)
            current_embed = discord.Embed(title="All Quotes (continued)", color=0x1E3A8A)
            field_count = 0
        
        current_embed.add_field(
            name=f"{q['author']}",
            value=f'"{q["text"]}" ({q["date"]})',
            inline=False
        )
        field_count += 1
    
    embeds.append(current_embed)
    
    await interaction.response.send_message(embed=embeds[0])
    for embed in embeds[1:]:
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="showauthors", description="Show all authors with number of quotes")
async def showauthors_slash(interaction: discord.Interaction):
    quotes = load_quotes()
    
    if not quotes:
        await interaction.response.send_message("No quotes yet.")
        return
    
    author_counts = {}
    author_original_names = {}
    
    for q in quotes:
        author_lower = q["author"].lower()
        author_counts[author_lower] = author_counts.get(author_lower, 0) + 1
        if author_lower not in author_original_names:
            author_original_names[author_lower] = q["author"]
    
    sorted_authors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)
    
    embed = discord.Embed(title="Authors", color=0x1E3A8A)
    
    for author_lower, count in sorted_authors:
        original_name = author_original_names[author_lower]
        category = categorize_author(count)
        embed.add_field(
            name=f"{original_name}",
            value=f"{count} quotes - {category}",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="show", description="Show quotes from specific author")
async def show_slash(interaction: discord.Interaction, author: str):
    if not author.strip():
        await interaction.response.send_message("Please provide an author name.", ephemeral=True)
        return
    
    quotes = load_quotes()
    author_lower = author.lower()
    
    filtered = [q for q in quotes if q["author"].lower() == author_lower]
    
    if not filtered:
        await interaction.response.send_message(f"No quotes found for {format_author_name(author)}")
        return
    
    display_name = filtered[0]["author"]
    
    embed = discord.Embed(
        title=f"Quotes by {display_name}",
        description=f"Total: {len(filtered)} quote{'s' if len(filtered) != 1 else ''}",
        color=0x1E3A8A
    )
    
    for q in filtered:
        embed.add_field(
            name=q["date"],
            value=f'"{q["text"]}"',
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="showrandom", description="Display a random quote")
async def showrandom_slash(interaction: discord.Interaction):
    quotes = load_quotes()
    
    if not quotes:
        await interaction.response.send_message("No quotes to display")
        return
    
    seed = f"{datetime.now().timestamp()}{interaction.user.id}"
    hash_obj = hashlib.md5(seed.encode())
    hash_int = int(hash_obj.hexdigest(), 16)
    index = hash_int % len(quotes)
    
    q = quotes[index]
    
    await interaction.response.send_message(f'"{q["text"]}" - {q["author"]} ({q["date"]})')

@bot.tree.command(name="dailyquote", description="Show today's quote")
async def dailyquote_slash(interaction: discord.Interaction):
    quotes = load_quotes()
    
    if not quotes:
        await interaction.response.send_message("No quotes to display")
        return
    
    index = get_daily_quote_index(quotes)
    q = quotes[index]
    
    await interaction.response.send_message(f'Daily Quote\n"{q["text"]}" - {q["author"]} ({q["date"]})')

@bot.tree.command(name="shutdown", description="Shutdown the bot (owner only)")
async def shutdown_slash(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("You don't have permission.", ephemeral=True)
        return
    
    await interaction.response.send_message("Shutting down...")
    await bot.close()

# -------------------------------
# Run the bot
# -------------------------------
if __name__ == "__main__":
    bot.run(TOKEN)