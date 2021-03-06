# Unreleased
* __[BUGFIX]__ Handle open pull request events.

# Farcy 1.3.0 (October 8, 2018)
* __[FEATURE]__ Ignore PRs which contain "farcy: ignore" in the PR description.


# Farcy 1.2.3 (March 19, 2018)
* __[BUGFIX]__ Fix issue with github3.py version 1.0.


# Farcy 1.2.1 (March 15, 2018)
* __[BUGFIX]__ Fix imports.


# Farcy 1.2 (March 15, 2018)
* __[FEATURE]__ Support user blacklists.


# Farcy 1.1 (January 13, 2015)
* __[FEATURE]__ Provide an SCSS-Lint handler for css and scss .css and .scss files.
* __[BUGIFX]__ Handle github3.exceptions.ServerErrors in the event loop.
* __[BUGFIX]__ Add catch-all for exceptions that could occur when handling a
  PullRequest or Push event.
* __[CHANGE]__ Drop python 3.2 support (not easily supported by coveralls and
  is minimally used:
  https://github.com/praw-dev/praw/pull/532#issuecomment-142110977).


# Farcy 1.0 (September 23, 2015)

* __[FEATURE]__ Automatically process new and updated pull requests from github
  repo.
* __[FEATURE]__ Enable config options to be given both in a config file and on
  the command line.
* __[FEATURE]__ Manually process a single pull request from the command line.
* __[FEATURE]__ Provide an ESLint handler for javascript .js and .jsx files
  (well tested).
* __[FEATURE]__ Provide a Flake8 handler for python .py files (minimally
  tested).
* __[FEATURE]__ Provide a JSXHint handler for javascript .js and .jsx files
  (moderately tested).
* __[FEATURE]__ Provide a Pep257 handler for python .py files (minimally
  tested).
* __[FEATURE]__ Provide a Rubocop handler for ruby .rb files (well tested).
* __[FEATURE]__ Support a maximum visible Farcy comment limit on a single pull
request.
* __[FEATURE]__ Support file exclusion paths.
  file.
* __[FEATURE]__ Support user whitelists.
