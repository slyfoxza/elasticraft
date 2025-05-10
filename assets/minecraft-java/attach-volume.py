#!/usr/bin/env python3
# Copyright 2019, 2025 Philip Cronje
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
import boto3
import requests
import sys
import time

token = requests.put(
    "http://169.254.169.254/latest/api/token",
    headers={"X-aws-ec2-metadata-token-ttl-seconds": str(21600)},
).text
instance_id = requests.get(
    "http://169.254.169.254/latest/meta-data/instance-id",
    headers={"X-aws-ec2-metadata-token": token},
).text
region = requests.get(
    "http://169.254.169.254/latest/meta-data/placement/region",
    headers={"X-aws-ec2-metadata-token": token},
).text

with open("/etc/elasticraft/server-id") as f:
    server_id = f.read()

ec2 = boto3.resource("ec2", region_name=region)
volumes = list(
    ec2.volumes.filter(
        Filters=[
            {"Name": "tag:elasticraft:serverId", "Values": [server_id]},
            {"Name": "tag:elasticraft:volumeType", "Values": ["data-volume"]},
        ]
    )
)
if len(volumes) == 1:
    volume = volumes[0]
elif len(volumes) == 0:
    sys.exit(f"{sys.argv[0]}: No data volume found for {server_id}")
else:
    sys.exit(f"{sys.argv[0]}: Multiple data volumes found for {server_id}")

state = volume.attach_to_instance(Device="xvdm", InstanceId=instance_id)["State"]
while state == "attaching" or state != "attached":
    time.sleep(0.2)
    volume.reload()
    for attachment in volume.attachments:
        if attachment["InstanceId"] == instance_id:
            state = attachment["State"]
            break
    else:
        sys.exit(f"{sys.argv[0]}: Volume is no longer attached to {instance_id}")

if state != "attached":
    sys.exit(
        f"{sys.argv[0]}: {volume.id} did not attach to {instance_id}, state was {state}"
    )
else:
    print(f"{sys.argv[0]}: Attached {volume.id} to {instance_id} at /dev/xvdm")
