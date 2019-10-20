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
import aws_xray_sdk.core
import boto3
import google.auth.transport.urllib3
import google.oauth2.id_token
import os
import urllib3

aws_xray_sdk.core.patch(["boto3"])
http = urllib3.PoolManager()
request = google.auth.transport.urllib3.Request(http)
table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])


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

    results = table.query(
            Select="SPECIFIC_ATTRIBUTES",
            KeyConditionExpression=boto3.dynamodb.conditions.Key("userId").eq(decoded_token["sub"]),
            ProjectionExpression="userId")

    arn_prefix = event["methodArn"].partition("/")[0]
    policy = {
        "principalId": decoded_token["sub"],
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "execute-api:Invoke",
                    "Resource": f"{arn_prefix}/*/GET/server"
                }
            ]
        }
    }

    if len(results["Items"]) > 0 and results["Items"][0]["userId"] == decoded_token["sub"]:
        print(f"Authorizing {decoded_token['sub']} ({decoded_token['email']}) to POST to /server resource")
        policy["policyDocument"]["Statement"].append({
            "Effect": "Allow",
            "Action": "execute-api:Invoke",
            "Resource": f"{arn_prefix}/*/POST/server"
        })
    else:
        print(f"Authorizing {decoded_token['sub']} ({decoded_token['email']}) with read-only access")
    return policy
