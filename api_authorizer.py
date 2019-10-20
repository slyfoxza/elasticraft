# Copyright 2019 Philip Cronje
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and limitations under the License.
import google.auth.transport.urllib3
import google.oauth2.id_token
import os
import urllib3

http = urllib3.PoolManager()
request = google.auth.transport.urllib3.Request(http)


def handler(event, context):
    # The input includes the "Bearer " prefix, so strip it out.
    encoded_token = event["authorizationToken"][7:]
    try:
        decoded_token = google.oauth2.id_token.verify_token(encoded_token, request, os.environ["CLIENT_ID"])
    except ValueError:
        raise Exception("Unauthorized")

    if decoded_token["iss"] not in ("accounts.google.com", "https://accounts.google.com"):
        print(f"Unexpected token issuer {decoded_token['iss']}, rejecting call")
        raise Exception("Unauthorized")

    print(repr(decoded_token))
    raise Exception("Unauthorized")
