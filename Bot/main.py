# mypy: disable-error-code=attr-defined
import os
import sys
import praw  # type: ignore
import time
import utils
import prawcore  # type: ignore
import traceback
import datetime as dt
from pathlib import Path
from logger import Logger
from typing import (
    Optional,
    Callable,
    Tuple,
    List,
    Set,
    Any,
)

import importlib
import importlib.util
from bot import (
    Datatype,
    Posts,
    Row,
)
from update_checker import start_update_checker

# configuration will be loaded later once we have ensured the package is
# in place.  this avoids import errors when the ``config`` directory is
# provided via a volume mount that is initially empty.

cfg = None  # type: ignore
TEMPLATE = None  # type: ignore

# fallback template used when the config module cannot yet be imported
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


# the old JSON-based interactive configuration helper has been removed.  the
# values are now stored in ``config/config.py``.  ``cfg`` above is a simple
# dict containing the settings; callers should treat numeric entries as
# integers.



config_dir = Path(utils.BASE_DIR, 'config')
config_dir.mkdir(parents=True, exist_ok=True)
# make config a package so it can be imported later; if __init__.py is missing
# (for example a freshly mounted empty volume), create a minimal one.
init_file = config_dir / "__init__.py"
if not init_file.exists():
    init_file.write_text("# config package\n")

config_path = config_dir / 'config.py'
# if the config file itself is missing, write the template and exit. we need to
# import the template name from the module, but since the file was just created
# we'll import once below after ensuring the package exists.
if not config_path.exists():
    # write fallback template if we haven't yet imported the module
    fallback = TEMPLATE or DEFAULT_TEMPLATE
    config_path.write_text(fallback)
    print(f"Created new configuration template at {config_path!r}.\n"
          "Please populate the values and restart the bot.")
    sys.exit(0)

# now that the package structure exists and config file is present, import it
import importlib
spec = importlib.util.spec_from_file_location("config", str(config_path))
config_mod = importlib.util.module_from_spec(spec)
# insert into sys.modules so conventional imports work
sys.modules["config"] = config_mod
if spec.loader:
    spec.loader.exec_module(config_mod)  # type: ignore
cfg = config_mod.config
# older config files may not define TEMPLATE (previous bug); fall back
TEMPLATE = getattr(config_mod, 'TEMPLATE', DEFAULT_TEMPLATE)

posts = Posts('deleted_posts', config_dir)
logger = Logger(1)
untracked_flairs = (utils.Flair.ABANDONED,)
posts.init()
reddit = praw.Reddit(
    client_id=cfg['client_id'],
    client_secret=cfg['client_secret'],
    user_agent=cfg['user_agent'],
    username=cfg['username'],
    password=cfg['password'],
)


def remove_method(submission: praw.reddit.Submission) -> Optional[str]:
    removed = submission.removed_by_category
    if removed is not None:
        # if removed in ('author', 'moderator'):
        #     method = 'Removed by moderator'
        if removed in ('author',):
            method = 'Deleted by OP'
        elif removed in ('moderator',):
            method = 'Removed by mod'
        elif removed in ('deleted',):
            method = 'Deleted by user'
        else:
            method = 'Uknown deletion method'
        return method

    return None


def send_modmail(reddit: praw.Reddit, subreddit: str, subject: str, msg: str) -> bool:
    # build the payload for the compose API
    # Note: The caller provides subject/msg; subreddit is used for the `to` field.
    data = {
        "subject": subject,
        "text": msg,
        "to": f"/r/{subreddit}",
    }
    try:
        print("Sending modmail via api/compose/")
        reddit.post("api/compose/", data=data)
        return True
    except prawcore.exceptions.ResponseException as e:
        if "RATELIMIT" in str(e):
            print(f"[RATE LIMIT] Modmail rate limited: {e}")
            return False
        print("Failed to send modmail with new method")
        import traceback
        print("Exception details:", repr(e))
        print(traceback.format_exc())
        return False
    except Exception as e:
        print("Failed to send modmail with new method")
        import traceback
        print("Exception details:", repr(e))
        print(traceback.format_exc())
        return False


def notify_if_error(func: Callable[..., int]) -> Callable[..., int]:
    def wrapper(*args: Any, **kwargs: Any) -> int:
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            logger.debug("\nProgram interrupted by user")
            return 0
        except:
            author = 'https://www.reddit.com/user/kaerfkeerg'
            full_error = traceback.format_exc()
            bot_name = utils.BOT_NAME
            msg = f"Error with '{bot_name}':\n\n{full_error}\n\n"
            print("[ERROR] Exception occurred in main():")
            print(full_error)
            result = send_modmail(
                reddit,
                cfg['sub_name'],
                f'An error has occured with {utils.BOT_NAME} msg',
                msg
            )
            if not result:
                print("[ERROR] Failed to send error modmail")
            return 1
    return wrapper


def should_be_tracked(
        flair: utils.Flair,
        untracked_flairs: Tuple[utils.Flair, ...]) -> bool:
    return flair not in untracked_flairs


def user_is_deleted(submission: praw.reddit.Submission) -> bool:
    return submission.author is None


def check_submission(submission: praw.reddit.Submission, saved_submission_ids: Set[Row]) -> None:
    if not user_is_deleted(submission) and submission.id not in saved_submission_ids:
        flair = utils.get_flair(submission.link_flair_text)
        method = remove_method(submission)
        if should_be_tracked(flair, untracked_flairs):
            if method is None and submission.author is not None:
                original_post = Row(
                    username=submission.author.name,
                    title=submission.title,
                    text=submission.selftext,
                    post_id=submission.id,
                    deletion_method=Datatype.NULL,
                    post_last_edit=Datatype.NULL,
                    record_created=str(dt.datetime.now()),
                    record_edited=str(dt.datetime.now()),
                    subreddit=submission.subreddit.display_name,
                )
                posts.save(original_post)


@notify_if_error
def main() -> int:
    # announce startup and interval
    sleep_minutes = int(cfg.get('sleep_minutes', 5))
    logger.info(f"{utils.BOT_NAME} v{utils.BOT_VERSION} starting; will sleep {sleep_minutes} minutes between cycles")

    # Start update checker thread
    start_update_checker(
        reddit,
        cfg['sub_name'],
        utils.BOT_NAME,
        getattr(utils, 'BOT_VERSION', '0.1')
    )

    # run indefinitely, sleeping between iterations
    while True:
        posts_to_delete: Set[Row] = set()
        ignore_methods = ['Removed by mod',]

        logger.info("Starting new cycle...")
        cycle_start = time.time()

        if utils.parse_cmd_line_args(sys.argv, logger, config_path, posts):
            return 0

        # Fetch ban template and comment template once per cycle for efficiency
        ban_template = utils.get_ban_template_from_wiki(reddit, cfg['sub_name'], cfg.get('ban_wiki_page', 'ban-template'))
        comment_template = utils.get_comment_template_from_wiki(reddit, cfg['sub_name'], cfg.get('ban_wiki_page', 'ban-template'))
        logger.info(f"Loaded templates from wiki page '{cfg.get('ban_wiki_page', 'ban-template')}'")

        saved_submission_ids = {row.post_id for row in posts.fetch_all()}
        max_posts = cfg.get('max_posts')
        limit = int(max_posts) if max_posts else None
        sub_name = cfg['sub_name']

        for submission in reddit.subreddit(sub_name).new(limit=limit):
            try:
                check_submission(submission, saved_submission_ids)
            except prawcore.exceptions.TooManyRequests:
                logger.warning("[RATE LIMIT] Hit rate limit while fetching new submissions. Sleeping for 60 seconds...")
                time.sleep(60)
                check_submission(submission, saved_submission_ids)

        for stored_post in posts.fetch_all():
            try:
                submission = reddit.submission(id=stored_post.post_id)
                max_days = int(cfg['max_days'])
                created = utils.string_to_dt(stored_post.record_created).date()
                flair = utils.get_flair(submission.link_flair_text)

                if utils.submission_is_older(created, max_days) or flair in untracked_flairs:
                    posts_to_delete.add(stored_post)
                    continue

                method = remove_method(submission)
                
                if method is not None and not stored_post.deletion_method:
                    logger.info(f"[POST_DELETED_BLOCK] Post deletion detected for {stored_post.post_id}, method={method}")
                    if method not in ignore_methods:
                        logger.info(f"[POST_DELETED_BLOCK] Post {stored_post.post_id} not in ignore list, proceeding")
                        stored_post.deletion_method = method
                        stored_post.record_edited = str(dt.datetime.now())
                        posts.edit(stored_post)
                        
                        # Post archive comment
                        try:
                            logger.info(f"[POST_DELETED_BLOCK] Posting comment on {stored_post.post_id}")
                            comment_text = comment_template.format(
                                post_author=stored_post.username,
                                post_title=stored_post.title,
                                post_body=stored_post.text
                            )
                            comment = submission.reply(comment_text)
                            comment.mod.distinguish(sticky=True)
                            logger.info(f"[POST_DELETED_BLOCK] Comment posted: {comment.id}")
                        except Exception as e:
                            logger.warning(f"[POST_DELETED_BLOCK] Failed to post comment on {stored_post.post_id}: {e}")
                        
                        msg = utils.modmail_removal_notification(stored_post, method, ban_template, cfg['sub_name'])
                        result = send_modmail(
                            reddit,
                            cfg['sub_name'],
                            'A post has been deleted',
                            msg
                        )
                        if not result:
                            logger.warning(f"Failed to send modmail for deleted post: {stored_post.post_id}")
                    posts_to_delete.add(stored_post)
                    time.sleep(utils.MSG_AWAIT_THRESHOLD)

                elif user_is_deleted(submission):
                    logger.info(f"[USER_DELETED_BLOCK] User account deleted for {stored_post.post_id}")
                    if method not in ignore_methods:
                        logger.info(f"[USER_DELETED_BLOCK] Sending modmail")
                        
                        # Post archive comment
                        try:
                            logger.info(f"[USER_DELETED_BLOCK] Posting comment on {stored_post.post_id}")
                            comment_text = comment_template.format(
                                post_author=stored_post.username,
                                post_title=stored_post.title,
                                post_body=stored_post.text
                            )
                            comment = submission.reply(comment_text)
                            comment.mod.distinguish(sticky=True)
                            logger.info(f"[USER_DELETED_BLOCK] Comment posted: {comment.id}")
                        except Exception as e:
                            logger.warning(f"[USER_DELETED_BLOCK] Failed to post comment on {stored_post.post_id}: {e}")
                        
                        result = send_modmail(
                            reddit,
                            cfg['sub_name'],
                            "User's account has been deleted",
                            utils.modmail_removal_notification(stored_post, 'Account has been deleted', ban_template, cfg['sub_name'])
                        )
                        if not result:
                            logger.warning(f"Failed to send modmail for deleted user: {stored_post.post_id}")
                    posts_to_delete.add(stored_post)
                    posts_to_delete.add(stored_post)
                    time.sleep(utils.MSG_AWAIT_THRESHOLD)

                if submission.selftext != stored_post.text\
                        or submission.selftext != stored_post.post_last_edit\
                            and not stored_post.deletion_method:
                    stored_post.post_last_edit = submission.selftext
                    stored_post.record_edited = str(dt.datetime.now())
                    posts.edit(stored_post)
            except prawcore.exceptions.TooManyRequests:
                logger.warning("[RATE LIMIT] Hit rate limit while processing stored posts. Sleeping for 60 seconds...")
                time.sleep(60)

        for row in posts_to_delete:
            posts.delete(post_id=row.post_id)

        posts_to_delete.clear()
        
        # Calculate cycle duration
        cycle_elapsed = time.time() - cycle_start
        cycle_minutes = cycle_elapsed / 60
        
        logger.info("Program finished successfully")
        logger.info(f"Total posts deleted: {len(posts_to_delete)}")
        logger.info(f"Cycle completed in {cycle_elapsed:.2f} seconds ({cycle_minutes:.2f} minutes)")

        # wait before the next cycle
        sleep_minutes = int(cfg.get('sleep_minutes', 5))
        logger.info(f"Sleeping for {sleep_minutes} minutes...")
        time.sleep(sleep_minutes * 60)

    # end of while True
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        import traceback
        print("[FATAL] Uncaught exception in main():", repr(e))
        print(traceback.format_exc())
        sys.exit(1)