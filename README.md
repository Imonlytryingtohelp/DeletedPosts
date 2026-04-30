# DeletedPosts Bot

## Description

DeletedPosts Bot monitors a specified subreddit for deleted posts and notifies moderators via modmail. It is designed to run continuously and can be easily deployed using Docker. Configuration is handled via environment variables or a Python config file.

## Quick Install (Docker)

1. Clone this repository:
   ```sh
   git clone https://github.com/yourusername/DeletedPosts.git
   cd DeletedPosts
   ```

2. Copy `example.env` to `.env` and fill in your Reddit API credentials and bot settings:
   ```env
   CLIENT_ID=your_client_id_here
   CLIENT_SECRET=your_client_secret_here
   USER_AGENT="DeletedPostsBot/1.0 by YourUsername"
   USERNAME=bot_username
   PASSWORD=bot_password
   SUB_NAME=example_subreddit
   MAX_DAYS=180
   MAX_POSTS=180
   SLEEP_MINUTES=5
   ```

3. Use the provided `docker-compose.yml` file:
   ```sh
   docker-compose up -d
   ```

The bot will automatically generate its configuration from your environment variables each time the container starts.

---

## Advanced Install

If you want to customize the Docker setup or run the bot outside Docker:

1. Build your own Docker image:
   ```sh
   git clone https://github.com/yourusername/DeletedPosts.git
   cd DeletedPosts
   docker build -t deletedposts .
   ```

2. Create an `.env` file (or use `example.env`) with your Reddit API credentials and bot settings.

3. Run the container manually:
   ```sh
   docker run --env-file .env deletedposts
   ```

Or run the bot directly on your host:
   ```sh
   python Bot/main.py
   ```

---

## Configuration

### Ban Template

The ban template is now loaded from a subreddit wiki page in YAML format. This allows moderators to update the ban message without restarting the bot.

#### Environment Variables & Config

Set the wiki page name via the `BAN_WIKI_PAGE` environment variable (default: `ban-template`):

**Docker Compose (.env file):**
```env
BAN_WIKI_PAGE=ban-template
REDDIT_BAN_WIKI_PAGE=${BAN_WIKI_PAGE}
```

**Direct Python:**
The config file (`config/config.py`) includes a `ban_wiki_page` setting.

#### Wiki Page Setup

1. Create or edit a wiki page on your subreddit with the name specified in `BAN_WIKI_PAGE` (default: `ban-template`)
2. Add the following YAML content:

```yaml
ban_template: |
  [Deleted post](https://reddit.com/comments/{post_id}).

  Deleting an answered post without marking it solved is against our rules.

  You can read [our rules](https://reddit.com/r/YourSub/wiki/rules) for appeal information.
```

**Key Features:**
- Use `{post_id}` as a placeholder that will be replaced with the actual post ID
- Multi-line templates are fully supported (use YAML's pipe syntax `|`)
- If the wiki page doesn't exist or can't be parsed, the bot will use a fallback message

You can  reset the configuration back to the default template by invoking
``reset_config`` on the command line:

```
python -m Bot.main reset_config
```

Other command line actions (``help`` and ``reset_db``) remain unchanged.
