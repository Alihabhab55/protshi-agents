"""W05-D6 - prove the default push sends NOTHING: block the network and run it.

Run:  python test_push_dryrun.py
"""

import sys

import requests

import push
from catalog import connect


def no_network(*args, **kwargs):
    raise AssertionError(f"the dry run tried to use the network: {args[:1]}")


# Any attempt to talk to Shopify (token, upload, GraphQL) now fails the test loudly.
requests.post = requests.put = requests.get = no_network


def snapshot():
    con = connect()
    rows = [tuple(r) for r in con.execute("SELECT * FROM products ORDER BY id")]
    con.close()
    return rows


before = snapshot()
for argv in (["push.py", "--limit", "1"], ["push.py", "--dry-run"], ["push.py", "bag-005"]):
    print(f"\n### {' '.join(argv)}")
    sys.argv = argv
    push.main()

assert snapshot() == before, "the dry run changed catalog.db"
print("\nAll dry-run checks passed: no network calls, catalog.db unchanged.")
