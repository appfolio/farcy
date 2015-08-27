"""Helper methods and classes."""


from collections import defaultdict
try:
    from configparser import ConfigParser  # PY3
    basestring = str
except ImportError:
    from ConfigParser import SafeConfigParser as ConfigParser  # PY2
from datetime import timedelta, tzinfo
from github3 import GitHub
from github3.exceptions import GitHubError
import logging
import os
import sys
from .const import FARCY_COMMENT_START, NUMBER_RE, CONFIG_DIR
from .exceptions import FarcyException

IS_FARCY_COMMENT = FARCY_COMMENT_START.split('v')[0]


def added_lines(patch):
    """Return a mapping of added line numbers to the patch line numbers."""
    added = {}
    lineno = None
    position = 0
    for line in patch.split('\n'):
        if line.startswith('@@'):
            lineno = int(NUMBER_RE.match(line.split('+')[1]).group(1))
        elif line.startswith(' '):
            lineno += 1
        elif line.startswith('+'):
            added[lineno] = position
            lineno += 1
        elif line == "\ No newline at end of file":
            continue
        else:
            assert line.startswith('-')
        position += 1
    return added


def ensure_config_dir():
    """Ensure Farcy config dir exists."""
    if not os.path.isdir(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, mode=0o700)


def extract_issues(text):
    """Extract farcy violations from a text."""
    if not is_farcy_comment(text):
        return []
    # Strip out start of bullet point, ignore first line
    return [line[2:] for line in text.split('\n')[1:]]


def filter_comments_from_farcy(comments):
    """Filter comments for farcy comments."""
    return (comment for comment in comments if is_farcy_comment(comment.body))


def filter_comments_by_path(comments, path):
    """Filter a comments iterable by a file path."""
    return (comment for comment in comments if comment.path == path)


def get_session():
    """Fetch and/or load API authorization token for GITHUB."""
    ensure_config_dir()
    credential_file = os.path.join(CONFIG_DIR, 'github_auth')
    if os.path.isfile(credential_file):
        with open(credential_file) as fd:
            token = fd.readline().strip()
        gh = GitHub(token=token)
        try:  # Test connection before starting
            gh.is_starred('github', 'gitignore')
            return gh
        except GitHubError as exc:
            raise_unexpected(exc.code)
            sys.stderr.write('Invalid saved credential file.\n')

    from getpass import getpass
    from github3 import authorize

    user = prompt('GITHUB Username')
    try:
        auth = authorize(
            user, getpass('Password for {0}: '.format(user)), 'repo',
            'Farcy Code Reviewer',
            two_factor_callback=lambda: prompt('Two factor token'))
    except GitHubError as exc:
        raise_unexpected(exc.code)
        raise FarcyException(exc.message)

    with open(credential_file, 'w') as fd:
        fd.write('{0}\n{1}\n'.format(auth.token, auth.id))
    return GitHub(token=auth.token)


def is_farcy_comment(text):
    """Return boolean if text was generated by Farcy."""
    return text.startswith(IS_FARCY_COMMENT)


def issues_by_line(comments, path):
    """Return dictionary mapping patch line nr to list of issues for a path."""
    by_line = defaultdict(list)
    for comment in filter_comments_by_path(comments, path):
        issues = extract_issues(comment.body)
        if issues:
            by_line[comment.position].extend(issues)
    return by_line


def parse_bool(value):
    """Return whether or not value represents a True or False value."""
    if isinstance(value, basestring):
        return value.lower() in ['1', 'on', 't', 'true', 'y', 'yes']
    return bool(value)


def parse_set(item_or_items, normalize=False):
    """Return a set of unique tokens in item_or_items.

    :param item_or_items: Can either be a string, or an iterable of strings.
      Each string can contain one or more items separated by commas, these
      items will be expanded, and empty tokens will be removed.
    :param normalize: When true, lowercase all tokens.

    """
    if isinstance(item_or_items, basestring):
        item_or_items = [item_or_items]

    items = set()
    for item in item_or_items:
        for token in (x.strip() for x in item.split(',') if x.strip()):
            items.add(token.lower() if normalize else token)
    return items if items else None


def plural(items, word):
    """Return number of items followed by the right form  of ``word``.

    ``items`` can either be an int or an object whose cardinality can be
    discovered via `len(items)`.

    The plural of ``word`` is assumed to be made by adding an ``s``.

    """
    item_count = items if isinstance(items, int) else len(items)
    word = word if item_count == 1 else word + 's'
    return '{0} {1}'.format(item_count, word)


def prompt(msg):
    """Output message and return striped input."""
    sys.stdout.write('{0}: '.format(msg))
    sys.stdout.flush()
    return sys.stdin.readline().strip()


def raise_unexpected(code):
    """Called from with in an except block.

    Re-raises the exception if we don't know how to handle it.

    """
    if code != 401:
        raise


def split_dict(data, keys):
    """Split a dict in a dict with keys `keys` and one with the rest."""
    with_keys = {}
    without_keys = {}
    for key, value in data.items():
        if key in keys:
            with_keys[key] = value
        else:
            without_keys[key] = value
    return with_keys, without_keys


def subtract_issues_by_line(by_line, by_line2):
    """Return a dict with all issues in by_line that are not in by_line2."""
    result = {}
    for key, values in by_line.items():
        exclude = by_line2.get(key, [])
        filtered = [value for value in values if value not in exclude]
        if filtered:
            result[key] = filtered
    return result


class Config(object):

    """Holds configuration for Farcy."""

    ATTRIBUTES = {'debug', 'exclude_paths', 'limit_users', 'log_level',
                  'pr_issue_report_limit', 'start_event'}
    LOG_LEVELS = {'CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'}
    PATH = os.path.join(CONFIG_DIR, 'farcy.conf')

    @property
    def log_level_int(self):
        """Int value of the log level."""
        return getattr(logging, self.log_level)

    @property
    def session(self):
        """Return GitHub session. Create if necessary."""
        if self._session is None:
            self._session = get_session()
        return self._session

    def __init__(self, repository, **overrides):
        """Initialize a config with default values."""
        self._session = None
        self.repository = repository
        self.set_defaults()
        self.load_config_file()
        self.override(**overrides)

    def __repr__(self):
        """String representation of the config."""
        keys = sorted(x for x in self.__dict__ if not x.startswith('_')
                      and x != 'repository')
        arg_fmt = ', '.join(['{0}={1!r}'.format(key, getattr(self, key))
                             for key in keys])
        return 'Config({0!r}, {1})'.format(self.repository, arg_fmt)

    def __setattr__(self, attr, value):
        """
        Set new config attribute.

        Validates new attribute values and tracks if changed from default.

        """
        if attr == 'debug' and parse_bool(value):
            # Force log level when in debug mode
            setattr(self, 'log_level', 'DEBUG')
        elif attr == 'exclude_paths':
            if value is not None:
                value = parse_set(value)
        elif attr == 'limit_users':
            if value:
                value = parse_set(value, normalize=True)
        elif attr == 'log_level' and self.debug:
            return  # Don't change level in debug mode
        elif attr == 'log_level' and value is not None:
            value = value.upper()
            if value not in self.LOG_LEVELS:
                raise FarcyException('Invalid log level: {0}'.format(value))
        elif attr == 'repository' and value is not None:
            repo_parts = value.split('/')
            if len(repo_parts) != 2:
                raise FarcyException('Invalid repository: {0}'.format(value))
        elif attr in ('pr_issue_report_limit', 'start_event'):
            if value is not None:
                value = int(value)
        super(Config, self).__setattr__(attr, value)

    def load_config_file(self):
        """Load value overrides from configuration file."""
        if not os.path.isfile(self.PATH):
            return

        config_file = ConfigParser()
        config_file.read(self.PATH)

        if not self.repository and \
                config_file.has_option('DEFAULT', 'repository'):
            self.repository = config_file.get('DEFAULT', 'repository')

        self.override(**dict(config_file.items(
            self.repository if config_file.has_section(self.repository)
            else 'DEFAULT')))

    def override(self, **overrides):
        """Override the config values passed as keyword arguments."""
        for attr, value in overrides.items():
            if attr in self.ATTRIBUTES and value:
                setattr(self, attr, value)

    def set_defaults(self):
        """Set the default config values."""
        self.start_event = None
        self.debug = False
        self.exclude_paths = None
        self.limit_users = None
        self.log_level = 'ERROR'
        self.pr_issue_report_limit = 128

    def user_whitelisted(self, user):
        """Return if user is whitelisted."""
        return self.limit_users is None or user.lower() in self.limit_users


class UTC(tzinfo):

    """Provides a simple UTC timezone class.

    Source: http://docs.python.org/release/2.4.2/lib/datetime-tzinfo.html

    """

    dst = lambda x, y: timedelta(0)
    tzname = lambda x, y: 'UTC'
    utcoffset = lambda x, y: timedelta(0)
