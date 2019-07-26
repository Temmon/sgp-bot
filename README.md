# sgp-bot
Reddit bot for SuperGreatParents sub

Set up a python virtualenv (python -m venv env)

Activate it (source env/bin/activate)

Install requirements (pip install -r requirements.txt)

Set up prodconf.py with environment specific variables. It needs DIR_PATH, which is the absolute path to the folder to save logs and the jobs file to. It needs BOT_CONF, which is a dictionary with the configuration variables needed to authenticate the bot. SGP-bot's info is on the SGP wiki. See praw's documentation for full details. 

Run (autopost.py)

It'll run indefinitely, but should stop gracefully with a kill signal.

I ran it in a daemon so it would auto start when the server started.

Don't commit prodconf.py to github. We don't want our password and configuration specific data saved there. It's in .gitignore on purpose. jobs.sqlite is transient and will be created when the program runs. It doesn't need to be stored. 