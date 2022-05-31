from __future__ import absolute_import
from base.celeryapp import app


@app.task
def test(params):
    print("Run with params: {}".format(params))
    return

