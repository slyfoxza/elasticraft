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
import boto3
import json
import time
import random

BASE_RETRY_DELAY = 0.01
MAX_RETRY_DELAY = 1.0
ec2 = boto3.resource('ec2')


def handle_start(request_id):
    instances = list(ec2.instances.filter(Filters=[
        {"Name": "tag:elasticraft", "Values": ["instance"]},
        {"Name": "instance-state-name", "Values": ["pending", "running", "shutting-down", "stopping",
                                                   "stopped"]}]))
    if len(instances) >= 1:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Elasticraft instance already exists"})
        }

    launch_templates = list(ec2.meta.client.describe_launch_templates(Filters=[
        {"Name": "tag:elasticraft", "Values": ["launchTemplate"]}])['LaunchTemplates'])
    if len(launch_templates) != 1:
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Failed to start server instance"})
        }

    instances = ec2.create_instances(MinCount=1, MaxCount=1, ClientToken=request_id, LaunchTemplate={
        "LaunchTemplateId": launch_templates[0]["LaunchTemplateId"]})
    sleep_time = BASE_RETRY_DELAY
    while instances[0].public_ip_address is None:
        time.sleep(sleep_time)
        sleep_time = random.uniform(BASE_RETRY_DELAY, sleep_time * 3)
        sleep_time = sleep_time if sleep_time < MAX_RETRY_DELAY else MAX_RETRY_DELAY
        instances[0].reload()
    return {
        "statusCode": 200,
        "body": json.dumps({"ipAddress": instances[0].public_ip_address})
    }


def handle_stop():
    return {
        "statusCode": 501,
        "body": json.dumps({"message": "The requested operation has not been implemented"})
    }


def handler(event, context):
    request = json.loads(event["body"])
    if request["operation"] == "start":
        return handle_start(event["requestContext"]["requestId"])
    elif request["operation"] == "stop":
        return handle_stop()
    else:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Invalid request body"})
        }
