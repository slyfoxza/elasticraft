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

ec2 = boto3.resource("ec2")


def handler(event, context):
    instance = ec2.Instance(event["detail"]["instance-id"])
    instance.load()

    for tag in instance.tags:
        if tag["Key"] == "elasticraft" and tag["Value"] == "instance":
            break
    else:
        print(f"Instance {instance.id} is not an Elasticraft instance, no action will be taken")
        return

    volumes = list(ec2.volumes.filter(Filters=[
        {"Name": "tag:elasticraft", "Values": ["dataVolume"]},
        {"Name": "status", "Values": ["available"]}]))
    if len(volumes) != 1:
        print(f"Expected exactly 1 volume, got: {volumes}")
        raise RuntimeError("Failed to locate Elasticraft data volume")

    print(f"Creating snapshot from {volumes[0].id}")
    snapshot = volumes[0].create_snapshot(
        Description="Automatic snapshot created on instance termination",
        TagSpecifications=[
            {"ResourceType": "snapshot", "Tags": [{"Key": "elasticraft", "Value": "dataVolumeSnapshot"}]}])
    print(f"Created {snapshot.id} from {volumes[0].id}")
