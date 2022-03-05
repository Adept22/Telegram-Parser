#!/bin/sh
set -e

if curl --fail ${API_URL}/ping; then
	exit 0
fi

exit 1
