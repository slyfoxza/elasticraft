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

aws_xray_sdk.core.patch(["boto3"])
ec2 = boto3.resource("ec2")
λ = boto3.client("lambda")


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
        payload = {
            "fqdn": os.environ["FQDN"],
            "ipAddress": instance.public_ip_address,
            "operation": "update",
            "recordType": "A"
        }
    elif event["detail"]["state"] == "terminated":
        payload = {
            "fqdn": os.environ["FQDN"],
            "operation": "delete",
            "recordType": "A"
        }
    print(f"Invoking {os.environ['ROUTE53CTL_ARN']} with payload: {repr(payload)}")
    λ.invoke(FunctionName=os.environ["ROUTE53CTL_ARN"], InvocationType="Event", Payload=json.dumps(payload))
    print("Successfully invoked Route 53 control function")
