# mypy: disable-error-code=attr-defined
import os
import datetime as dt
from bot import Posts
from pathlib import Path
from enum import Enum
from typing import List
from logger import Logger
from sqlitewrapper import Row
import praw  # type: ignore
import yaml


__all__ = (
    'Flair',
    'get_flair',
    'modmail_removal_notification',
    'parse_cmd_line_args',
    'submission_is_older',
    'string_to_dt',
    'get_ban_template_from_wiki',
    'get_comment_template_from_wiki',
)


class Flair(Enum):
    SOLVED = 'Solved'
    ABANDONED = 'Abandoned'
    UKNOWN = 'Uknown'


def get_flair(flair: str) -> Flair:
    try:
        return Flair(flair)
    except ValueError:
        return Flair('Uknown')


def get_ban_template_from_wiki(reddit: praw.Reddit, subreddit_name: str, wiki_page: str = "ban-template") -> str:
    """Load ban template from subreddit wiki page in YAML format.
    
    Args:
        reddit: PRAW Reddit instance
        subreddit_name: Name of the subreddit
        wiki_page: Name of the wiki page (default: "ban-template")
    
    Returns:
        The ban_template string from the wiki page, or a fallback message if not found
    """
    fallback_message = "Your custom ban message is not configured. Please contact the moderators for more information."
    
    try:
        subreddit = reddit.subreddit(subreddit_name)
        wiki = subreddit.wiki[wiki_page]
        content = wiki.content_md
        
        # Parse YAML content
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict) and "ban_template" in data:
                ban_template = data.get("ban_template", "").strip()
                if ban_template:
                    return ban_template
        except yaml.YAMLError as e:
            print(f"[WIKI] Error parsing YAML from wiki page '{wiki_page}': {e}")
        
        return fallback_message
    except Exception as e:
        print(f"[WIKI] Error loading ban template from wiki page '{wiki_page}': {e}")
        return fallback_message


def get_comment_template_from_wiki(reddit: praw.Reddit, subreddit_name: str, wiki_page: str = "ban-template") -> str:
    """Load comment template from subreddit wiki page in YAML format.
    
    Args:
        reddit: PRAW Reddit instance
        subreddit_name: Name of the subreddit
        wiki_page: Name of the wiki page (default: "ban-template")
    
    Returns:
        The comment_template string from the wiki page, or a default template if not found
    """
    fallback_template = "This post was deleted.\n\nAuthor: {post_author}\nTitle: {post_title}"
    
    try:
        subreddit = reddit.subreddit(subreddit_name)
        wiki = subreddit.wiki[wiki_page]
        content = wiki.content_md
        
        # Parse YAML content
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict) and "comment_template" in data:
                comment_template = data.get("comment_template", "").strip()
                if comment_template:
                    return comment_template
        except yaml.YAMLError as e:
            print(f"[WIKI] Error parsing YAML from wiki page '{wiki_page}': {e}")
        
        return fallback_template
    except Exception as e:
        print(f"[WIKI] Error loading comment template from wiki page '{wiki_page}': {e}")
        return fallback_template


def modmail_removal_notification(submission: Row, method: str, ban_template: str, subreddit: str = '') -> str:
    """Generate modmail notification for a removed post.
    
    Args:
        submission: The deleted post submission data
        method: The deletion method (e.g., 'Deleted by OP')
        ban_template: The pre-fetched ban template string
        subreddit: The subreddit name (optional)
    
    Returns:
        The formatted modmail message
    """
    ban_text = ban_template.format(post_id=submission.post_id)
    
    return f"""A post has been removed

OP: `{submission.username}`

Title: {submission.title}

Post ID: https://sh.reddit.com/comments/{submission.post_id}

Post ID (Old Reddit): https://old.reddit.com/comments/{submission.post_id}

Date created: {submission.record_created}

Date found: {submission.record_edited}

Ban Template:

```
{ban_text}
```
ModBox 1-Click ban: modbox://ban?user={submission.username}&reason=%5BDeleted+post%5D%28https%3A%2F%2Freddit.com%2Fcomments%2F{submission.post_id}%29.%0A++++%0ADeleting+a+post+with+comments%2C+without+following+our+%5Bpost+deletion+guide%5D%28https%3A%2F%2Fwww.reddit.com%2Fr%2FMinecraftHelp%2Fwiki%2Ffaq%2F%23wiki_how_do_i_delete_a_post.2C_without_breaking_rule_7.3F%29+is+against+our+rules.%0A%0AYou+can+read+%5Bour+rules%5D%28https%3A%2F%2Fsh.reddit.com%2Fr%2Fminecrafthelp%2Fwiki%2Frules%29+for+appeal+information.&note=Deleted+Post+30DTB&notetype=Temp+Ban&durationDays=30&subreddit={subreddit}


"""


# default template used when resetting the configuration.  this mirrors
# the template defined in ``config/config.py``; keeping a copy here avoids
# depending on the module itself being importable (which can fail if the
# directory is newly mounted or otherwise not part of sys.path).
DEFAULT_TEMPLATE = """# configuration for DeletedPosts bot
# edit the values of the dictionary below and restart the bot

config = {
    "client_id": "",
    "client_secret": "",
    "user_agent": "",
    "username": "",
    "password": "",
    "sub_name": "",
    # numeric settings are stored as integers here rather than strings
    "max_days": 180,
    "max_posts": 180,
    "sleep_minutes": 5,
    "ban_wiki_page": "ban-template",
}
"""

def parse_cmd_line_args(args: List[str], logger: Logger, config_file: Path, posts: Posts) -> bool:
    """Parse a very small set of operations from ``sys.argv``.

    ``config_file`` now refers to the Python configuration module path
    (typically ``.../config/config.py``).  ``reset_config`` will overwrite the
    file with a default template; the template is defined above to avoid
    importing the configuration module directly.
    """
    help_msg = """Command line help prompt
    Command: help
    Args: []
    Description: Prints the help prompt

    Command: reset_config
    Args: []
    Description: Overwrite the Python configuration file with default values

    Command: reset_db
    Args: []
    Description: Reset the database
"""
    if len(args) > 1:
        if args[1] == 'help':
            logger.info(help_msg)
        elif args[1] == 'reset_config':
            # write the default template text back to the configuration file.
            try:
                config_file.write_text(DEFAULT_TEMPLATE)
            except Exception:
                logger.error("Unable to reset configuration file")
        elif args[1] == 'reset_db':
            try:
                os.remove(posts.path)
            except FileNotFoundError:
                logger.error("No database found")
        else:
            logger.info(help_msg)
        return True
    return False


def submission_is_older(submission_date: dt.date, max_days: int) -> bool:
    current_date = dt.datetime.now().date()
    time_difference = current_date - submission_date
    if time_difference.days > max_days:
        return True
    return False


def string_to_dt(date_string: str) -> dt.datetime:
    return dt.datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S.%f')
