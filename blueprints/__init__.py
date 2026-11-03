# Namespace package for all Flask blueprints.
#
# Each subfolder (main, auth, admin, api, ...) owns one Blueprint and
# is registered onto the app inside the create_app() factory in
# app.py. Keeping every feature area in its own blueprint package is
# what lets the project grow (auth, admin, API, streaming) without
# routes.py turning into a single giant file.
