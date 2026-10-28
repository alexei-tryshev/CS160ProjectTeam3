import os

# Importing app.py builds an app at import time; point it at a throwaway
# database so the test suite never touches the real wellness_tracker data.
os.environ["MONGO_DB_NAME"] = "wellness_tracker_test"
