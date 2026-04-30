# Changelog for DeletedPostsBot

## v1.5.4

### Fixed
- **Removed duplicate modbox url link** Link now correctly displays once, under the ban template.  

## v1.5.3 

### Changed
- **Error message handling**: Removed author attribution line from error modmail notifications
  - Simplified error message format for cleaner communication
- **ModBox One-click ban link** added to modmail sent. 
---

## v1.5.0 

### Added
- **Configurable comment template system**: Bot now posts distinguished and stickied comments when detecting deleted posts
  - Created `get_comment_template_from_wiki()` function to fetch comment template from wiki page
  - Comment template loaded from the same wiki page as ban template (configurable via `ban_wiki_page` setting)
  - Supports multi-line templates using YAML syntax with key `comment_template`
  - Placeholder support for dynamic content: `{post_author}`, `{post_title}`, `{post_body}`
  - Comments are automatically distinguished (mod indicator) and stickied to top of thread
  - Uses stored post data to preserve full content even after user/post deletion

### Changed
- **Bot authorship**: Updated original author attribution in `__main__.py` while preserving original author credit
- **Comment content**: Comments now use preserved post data from database instead of live Reddit API
  - Ensures {post_author}, {post_title}, and {post_body} placeholders contain original content
  - Works correctly even when user account has been deleted

### Fixed
- Comment posting now correctly retrieves and displays original post content when user deletes their account

---

## v1.4.1 (2026-03-14)

### Changed
- **Tracking behavior**: Posts marked as "Solved" are now tracked and trigger modmail notifications when deleted
  - Only "Abandoned" posts are now ignored from tracking
  - Allows detection of deleted answered posts that were manually marked solved

---

## v1.4.0 (2026-03-13)

### Optimized
- **Major performance improvement**: Eliminated duplicate Reddit API submission fetch in main processing loop
  - Previously fetched the same submission twice for each stored post
  - Now reuses the first fetch for all deletion checks
  - **Result**: Cycle time reduced from ~5 minutes to ~1 minute (5x faster)
  - Tested and verified for accurate deletion detection on live subreddit

### Added
- Cycle timing instrumentation:
  - Bot now logs the duration of each cycle in both seconds and minutes.
  - Helps identify performance bottlenecks and track optimization effects.

---

## v1.3.2 (2026-03-13)

### Added
- Cycle timing instrumentation:
  - Bot now logs the duration of each cycle in both seconds and minutes.
  - Helps identify performance bottlenecks and track optimization effects.

---

## v1.3.1 (2026-03-13)

### Changed
- Improved ban template formatting in modmail notifications:
  - Ban template is now displayed in a markdown codeblock for better readability.
  - Codeblock preserves multi-line formatting and special characters.
  - Changed label from "Ban Template;" to "Ban Template:" for clarity.

---

## v1.3.0 (2026-03-13)

### Added
- Wiki-based ban template system: Ban messages are now loaded from a subreddit wiki page in YAML format.
  - Created `get_ban_template_from_wiki()` function to fetch and parse wiki content.
  - Wiki page is configurable via the `ban_wiki_page` config setting (default: `"ban-template"`).
  - Environment variable support: `REDDIT_BAN_WIKI_PAGE` for Docker deployments.
  - Supports multi-line templates using YAML syntax.
  - Allows moderators to update ban messages without restarting the bot.
- Enhanced cycle logging for better visibility:
  - Added "Starting new cycle..." log at the beginning of each cycle.
  - Added wiki page load confirmation log showing which page was loaded.
  - Added rate limiting warnings when API calls exceed Reddit's rate limits.

### Changed
- Updated `modmail_removal_notification()` function signature to accept pre-fetched `ban_template` string parameter (instead of fetching it for each post).
- Moved ban template from environment variable to wiki page configuration.
- Updated `populate_config.py` to include `ban_wiki_page` setting with fallback default.
- Added `PyYAML` dependency to Docker image for YAML parsing.
- Updated all template defaults to include `ban_wiki_page` setting.
- **Performance improvements**:
  - Ban template is now fetched once per cycle instead of for each post, preventing API slowdown during post processing.
  - Cycles now complete successfully without hanging or excessive delays.

### Removed
- Removed `REDDIT_BAN_TEMPLATE` environment variable and `ban_template` config key (replaced by wiki-based system).

---

## v1.2.2 (2026-03-12)

### Changed
- Updated modmail removal notification to include old.reddit link for easier post access.

---

## v1.2.1 (2026-03-11)

### Fixed
- Export `BOT_VERSION` in `utils/__all__` to fix AttributeError when accessing `utils.BOT_VERSION`.
- Improved error handling in `@notify_if_error` decorator to catch and log exceptions from modmail reporting.
- Added separate try-except for modmail calls in error handler to prevent cascading failures.

### Changed
- Added startup log to display bot version (`DeletedPostsBot v1.2.1 starting...`).
- Added top-level exception handler to log uncaught exceptions before exit.

---

## v1.2.0 (2026-03-11)

### Added
- Integrated update checker module for automatic version polling and modmail notifications.
  - Created `Bot/update_checker.py` with background thread and Reddit modmail support.
  - Added `start_update_checker()` call in `Bot/main.py`.
  - Set `BOT_VERSION` in `Bot/utils/constants.py`.

### Changed
- Updated environment variable names to use `REDDIT_` prefix throughout:
  - `.env` file
  - `docker-compose.yml`
  - `populate_config.py` loader
- Updated `config/config.py` to match new variable names and clarify usage.

### Fixed
- Synced Reddit username between `.env` and `config/config.py` to resolve authentication errors.
- Improved config loader to support new variable prefix and fallback.

---
For previous changes, see earlier changelog entries or commit history.
