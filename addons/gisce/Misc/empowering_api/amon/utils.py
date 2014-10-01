import logging
import os

from empowering import Empowering
import erppeek
from erppeek import lowercase
import pymongo
import redis
from raven import Client
from raven.conf import setup_logging as sentry_setup_logging
from raven.handlers.logging import SentryHandler


logger = logging.getLogger(__name__)


__REDIS_POOL = None


class Popper(object):
    def __init__(self, items):
        self.items = list(items)

    def pop(self, n):
        res = []
        for x in xrange(0, min(n, len(self.items))):
            res.append(self.items.pop())
        return res


class PoolWrapper(object):
    def __init__(self, pool, cursor, uid, context=None):
        self.pool = pool
        self.cursor = cursor
        self.uid = uid
        self.context = context

    def __getattr__(self, name):
        model = lowercase(name)
        return self.pool.get(model)


def config_from_environment(env_prefix, env_required=None, **kwargs):
    config = kwargs.copy()
    prefix = '%s_' % env_prefix.upper()
    for env_key, value in os.environ.items():
        env_key = env_key.upper()
        if env_key.startswith(prefix):
            key = '_'.join(key.split('_')[1:]).lower()
            config[key] = value
    if env_required:
        for required in env_required:
            if required not in config:
                logger.error('You must pass %s or define env var %s%s' %
                             (required, prefix, required.upper()))
    return config


def setup_peek(**kwargs):
    peek_config = config_from_environment('PEEK', **kwargs)
    logger.info("Using PEEK CONFIG: %s" % peek_config)
    return erppeek.Client(**peek_config)


def setup_mongodb(**kwargs):
    config = config_from_environment('MONGODB', ['host', 'database'], **kwargs)
    mongo = pymongo.MongoClient(host=config['host'])
    return mongo[config['database']]


def setup_empowering_api(**kwargs):
    config = config_from_environment('EMPOWERING', ['company_id'], **kwargs)
    em = Empowering(**config)
    return em


def setup_redis():
    global __REDIS_POOL
    if not __REDIS_POOL:
        __REDIS_POOL = redis.ConnectionPool()
    r = redis.Redis(connection_pool=__REDIS_POOL)
    return r


def setup_logging(logfile=None):
    logger = logging.getLogger('amon')
    if logfile:
        hdlr = logging.FileHandler(logfile)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        hdlr.setFormatter(formatter)
        logger.addHandler(hdlr)
    sentry = Client()
    sentry_handler = SentryHandler(sentry, level=logging.ERROR)
    sentry_setup_logging(sentry_handler)