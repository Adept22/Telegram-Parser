from __future__ import absolute_import
from base.celeryapp import app


@app.task
def test(params: str):
    print("Run with params: {}".format(params))
    return True

