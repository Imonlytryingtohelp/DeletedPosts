import os
import json

CONFIG_KEYS = [
    "client_id",
    "client_secret",
    "user_agent",
    "username",
    "password",
    "sub_name",
    "max_days",
    "max_posts",
    "sleep_minutes",
    "ban_wiki_page",
]

DEFAULTS = {
    "client_id": "",
    "client_secret": "",
    "user_agent": "",
    "username": "",
    "password": "",
    "sub_name": "",
    "max_days": 180,
    "max_posts": 180,
    "sleep_minutes": 5,
    "ban_wiki_page": "ban-template",
}

# Only read DPB_REDDIT_ prefixed environment variables
config = {}
for key in CONFIG_KEYS:
    env_val = os.getenv(f"DPB_REDDIT_{key.upper()}")
    if env_val is not None:
        # Cast numeric values
        if key in ["max_days", "max_posts", "sleep_minutes"]:
            try:
                config[key] = int(env_val)
            except ValueError:
                config[key] = DEFAULTS[key]
        else:
            config[key] = env_val
    else:
        config[key] = DEFAULTS[key]

# Write config.py
with open("config/config.py", "w", encoding="utf-8") as f:
    f.write('"""\nConfiguration for the DeletedPosts bot.\n"""\n\n')
    f.write('config = ' + json.dumps(config, indent=4) + '\n')
    f.write('\nTEMPLATE = f"""# configuration for DeletedPosts bot\n# edit the values of the dictionary below and restart the bot\n\nconfig = {config!r}\n"""\n')

print("config/config.py has been populated from environment variables.")
