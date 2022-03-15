#!/bin/sh
set -e

if curl --fail ${API_URL}/ping; then
	exit 1
fi

exit 0
