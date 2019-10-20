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

aws_xray_sdk.core.patch(["boto3"])
cors_headers = {
    "Access-Control-Allow-Headers": "Authorization,Content-Type",
    "Access-Control-Allow-Methods": "*",
    "Access-Control-Allow-Origin": "*"
}
ec2 = boto3.resource("ec2")


def handler(event, context):
    instances = list(ec2.instances.filter(Filters=[
        {"Name": "tag:elasticraft", "Values": ["instance"]},
        {"Name": "instance-state-name", "Values": ["pending", "running", "shutting-down", "stopping",
                                                   "stopped"]}]))
    if len(instances) == 0:
        return {
            "statusCode": 200,
            "body": json.dumps({"status": "stopped"}),
            "headers": cors_headers
        }
    elif len(instances) > 1:
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Failed to retrieve server status"}),
            "headers": cors_headers
        }
    else:
        body = {"status": "running"}
        if instances[0].state["Name"] == "pending":
            body["status"] = "starting"
        if instances[0].public_ip_address is not None:
            body["ipAddress"] = instances[0].public_ip_address
        return {
            "statusCode": 200,
            "body": json.dumps(body),
            "headers": cors_headers
        }
