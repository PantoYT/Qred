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
                quotes = json.load(f)
                # Migrate old quotes without IDs
                needs_save = False
                next_id = max([q.get("id", 0) for q in quotes], default=0) + 1
                for q in quotes:
                    if "id" not in q:
                        q["id"] = next_id
                        next_id += 1
                        needs_save = True
                if needs_save:
                    save_quotes(quotes)
                return quotes
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

def get_next_id(quotes):
    if not quotes:
        return 1
    return max([q.get("id", 0) for q in quotes]) + 1

def find_quote_by_id(quotes, quote_id):
    for q in quotes:
        if q.get("id") == quote_id:
            return q
    return None

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

def can_modify_quote(interaction, quote, owner_id):
    """Check if user can modify this quote"""
    # Owner can modify anything
    if interaction.user.id == owner_id:
        return True
    
    # Check if user is the author
    author_names = [a.strip() for a in quote["author"].split(",")]
    return interaction.user.name in author_names

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
    
    # Set daily quote as status
    quotes = load_quotes()
    if quotes:
        # Filter quotes that fit in status (max 128 chars)
        valid_quotes = [q for q in quotes if len(q["text"]) <= 128]
        
        if valid_quotes:
            index = get_daily_quote_index(valid_quotes)
            daily_quote = valid_quotes[index]
            
            await bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.custom,
                    name=daily_quote["text"]
                )
            )
        else:
            # All quotes too long, use fallback
            await bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name="Tracking your quotes | /commands"
                )
            )
    else:
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
    embed.add_field(name="/random", value="Display a random quote", inline=False)
    embed.add_field(name="/daily", value="Show today's quote", inline=False)
    embed.add_field(name="/add", value="Add quote(s) from recent messages", inline=False)
    embed.add_field(name="/create", value="Add a new quote manually", inline=False)
    embed.add_field(name="/mine", value="Show all your quotes", inline=False)
    embed.add_field(name="/edit", value="Edit one of your quotes", inline=False)
    embed.add_field(name="/delete", value="Delete one of your quotes", inline=False)
    embed.add_field(name="/all", value="Show all quotes (owner only)", inline=False)
    embed.add_field(name="/shutdown", value="Shut down the bot (owner only)", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="add", description="Add quote(s) from recent messages")
async def add_slash(
    interaction: discord.Interaction,
    messages: int = 1,
    author: str = None,
    skip: int = 0
):
    await interaction.response.defer()
    
    quotes_data = load_quotes()
    
    # Fetch more messages to account for skips and bot messages
    all_messages = [msg async for msg in interaction.channel.history(limit=50)]
    
    # Filter out bot messages
    non_bot_messages = [msg for msg in all_messages if not msg.author.bot]
    
    if not non_bot_messages:
        await interaction.followup.send("No suitable messages found in recent history.")
        return
    
    # Apply skip
    if skip >= len(non_bot_messages):
        await interaction.followup.send(f"Cannot skip {skip} messages, only {len(non_bot_messages)} available.")
        return
    
    available_messages = non_bot_messages[skip:]
    
    # Get requested number of messages
    if messages > len(available_messages):
        await interaction.followup.send(f"Cannot get {messages} messages, only {len(available_messages)} available after skip.")
        return
    
    selected_messages = available_messages[:messages]
    selected_messages.reverse()  # Oldest first for proper reading order
    
    # Filter by author if specified
    if author:
        author_lower = author.lower()
        selected_messages = [msg for msg in selected_messages if msg.author.name.lower() == author_lower]
        
        if not selected_messages:
            await interaction.followup.send(f"No messages found from author '{author}' in the selected range.")
            return
    
    # Validate messages
    if not selected_messages:
        await interaction.followup.send("No valid messages to add as quote.")
        return
    
    # Check for empty messages
    valid_messages = [msg for msg in selected_messages if msg.content.strip()]
    if not valid_messages:
        await interaction.followup.send("Cannot add empty messages as quote.")
        return
    
    # Build combined quote
    quote_lines = []
    authors = []
    seen_authors = set()
    
    for msg in valid_messages:
        quote_lines.append(msg.content.strip())
        author_lower = msg.author.name.lower()
        if author_lower not in seen_authors:
            authors.append(msg.author.name)
            seen_authors.add(author_lower)
    
    combined_text = "\n".join(quote_lines)
    
    if len(combined_text) > 500:
        await interaction.followup.send("Combined quote too long (max 500 characters).")
        return
    
    # Create author string
    if len(authors) == 1:
        author_str = authors[0]
    else:
        author_str = ", ".join(authors)
    
    date_str = datetime.now().strftime("%d/%m/%Y")
    
    new_quote = {
        "id": get_next_id(quotes_data),
        "text": combined_text,
        "author": author_str,
        "date": date_str
    }
    
    quotes_data.append(new_quote)
    save_quotes(quotes_data)
    
    preview = combined_text if len(combined_text) <= 100 else combined_text[:97] + "..."
    await interaction.followup.send(f'Quote #{new_quote["id"]} added: "{preview}" - {author_str} ({date_str})')

@bot.tree.command(name="create", description="Add a new quote manually")
async def create_slash(interaction: discord.Interaction, quote: str, author: str = None):
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
        "id": get_next_id(quotes),
        "text": quote.strip(),
        "author": author_name,
        "date": date_str
    }
    
    quotes.append(new_quote)
    save_quotes(quotes)
    
    await interaction.response.send_message(f'Quote #{new_quote["id"]} added: "{quote}" - {author_name} ({date_str})')

@bot.tree.command(name="edit", description="Edit one of your quotes")
async def edit_slash(interaction: discord.Interaction, quote_id: int, new_text: str):
    if not new_text.strip():
        await interaction.response.send_message("New text cannot be empty.", ephemeral=True)
        return
    
    if len(new_text) > 500:
        await interaction.response.send_message("New text too long (max 500 characters).", ephemeral=True)
        return
    
    quotes = load_quotes()
    quote = find_quote_by_id(quotes, quote_id)
    
    if not quote:
        await interaction.response.send_message(f"Quote #{quote_id} not found.", ephemeral=True)
        return
    
    if not can_modify_quote(interaction, quote, OWNER_ID):
        await interaction.response.send_message("You can only edit your own quotes.", ephemeral=True)
        return
    
    old_text = quote["text"]
    quote["text"] = new_text.strip()
    save_quotes(quotes)
    
    await interaction.response.send_message(
        f'Quote #{quote_id} updated!\n'
        f'Old: "{old_text}"\n'
        f'New: "{new_text}" - {quote["author"]} ({quote["date"]})'
    )

@bot.tree.command(name="delete", description="Delete one of your quotes")
async def delete_slash(interaction: discord.Interaction, quote_id: int):
    quotes = load_quotes()
    quote = find_quote_by_id(quotes, quote_id)
    
    if not quote:
        await interaction.response.send_message(f"Quote #{quote_id} not found.", ephemeral=True)
        return
    
    if not can_modify_quote(interaction, quote, OWNER_ID):
        await interaction.response.send_message("You can only delete your own quotes.", ephemeral=True)
        return
    
    quotes.remove(quote)
    save_quotes(quotes)
    
    await interaction.response.send_message(
        f'Quote #{quote_id} deleted: "{quote["text"]}" - {quote["author"]} ({quote["date"]})'
    )

@bot.tree.command(name="all", description="Show all quotes (owner only)")
async def all_slash(interaction: discord.Interaction):
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
            name=f"#{q['id']} - {q['author']}",
            value=f'"{q["text"]}" ({q["date"]})',
            inline=False
        )
        field_count += 1
    
    embeds.append(current_embed)
    
    await interaction.response.send_message(embed=embeds[0])
    for embed in embeds[1:]:
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="mine", description="Show all your quotes")
async def mine_slash(interaction: discord.Interaction):
    quotes = load_quotes()
    
    if not quotes:
        await interaction.response.send_message("No quotes yet.")
        return
    
    user_name = interaction.user.name
    
    # Find quotes where user is an author (handle multi-author quotes)
    filtered = []
    for q in quotes:
        author_names = [a.strip().lower() for a in q["author"].split(",")]
        if user_name.lower() in author_names:
            filtered.append(q)
    
    if not filtered:
        await interaction.response.send_message(f"You don't have any quotes yet, {user_name}!")
        return
    
    category = categorize_author(len(filtered))
    
    embed = discord.Embed(
        title=f"Quotes by {user_name}",
        description=f"Total: {len(filtered)} quote{'s' if len(filtered) != 1 else ''} - {category}",
        color=0x1E3A8A
    )
    
    for q in filtered:
        embed.add_field(
            name=f"#{q['id']} - {q['date']}",
            value=f'"{q["text"]}"',
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="random", description="Display a random quote")
async def random_slash(interaction: discord.Interaction):
    quotes = load_quotes()
    
    if not quotes:
        await interaction.response.send_message("No quotes to display")
        return
    
    seed = f"{datetime.now().timestamp()}{interaction.user.id}"
    hash_obj = hashlib.md5(seed.encode())
    hash_int = int(hash_obj.hexdigest(), 16)
    index = hash_int % len(quotes)
    
    q = quotes[index]
    
    await interaction.response.send_message(f'#{q["id"]}: "{q["text"]}" - {q["author"]} ({q["date"]})')

@bot.tree.command(name="daily", description="Show today's quote")
async def daily_slash(interaction: discord.Interaction):
    quotes = load_quotes()
    
    if not quotes:
        await interaction.response.send_message("No quotes to display")
        return
    
    index = get_daily_quote_index(quotes)
    q = quotes[index]
    
    await interaction.response.send_message(f'Daily Quote\n#{q["id"]}: "{q["text"]}" - {q["author"]} ({q["date"]})')

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