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
import json
import os
import urllib3

aws_xray_sdk.core.patch(["boto3"])
ec2 = boto3.resource("ec2")
http = urllib3.PoolManager()


def handler(event, context):
    instance = ec2.Instance(event["detail"]["instance-id"])
    instance.load()

    for tag in instance.tags:
        if tag["Key"] == "elasticraft" and tag["Value"] == "instance":
            break
    else:
        print(f"Instance {instance.id} is not an Elasticraft instance, no action will be taken")
        return

    if event["detail"]["state"] == "running":
        payload = {"content": "The Minecraft server has been started"}
    elif event["detail"]["state"] == "terminated":
        payload = {"content": "The Minecraft server has been stopped"}

    print(f"Invoking {os.environ['WEBHOOK_URL']} with payload: {repr(payload)}")
    subsegment = aws_xray_sdk.core.xray_recorder.begin_subsegment(os.environ["WEBHOOK_URL"], 'remote')
    try:
        response = http.request("POST", os.environ["WEBHOOK_URL"], body=json.dumps(payload),
                                headers={"Content-Type": "application/json"})
        subsegment.put_http_meta(aws_xray_sdk.core.models.http.STATUS, response.status)
    finally:
        aws_xray_sdk.core.xray_recorder.end_subsegment()

    if response.status >= 200 and response.status < 400:
        print("Successfully invoked notification webhook")
    else:
        raise RuntimeError(response.data.decode("UTF-8"))
