#!/bin/bash
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

# Install any pending software updates and additional software packages
amazon-linux-extras enable java-openjdk11
yum --assumeyes upgrade
yum --assumeyes install java-11-openjdk-headless python3
pip3 install boto3

# Discover some facts about the current instance
readonly instance_id=$(</var/lib/cloud/data/instance-id)
readonly region=$(curl --show-error --silent 'http://169.254.169.254/latest/dynamic/instance-identity/document'|python -c 'import json,sys;j=json.loads(sys.stdin.read());print(j["region"])')

# Download and install the CloudWatch agent
yum --assumeyes install "https://s3.$region.amazonaws.com/amazoncloudwatch-agent-$region/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm" && \
	ln /etc/amazon-cloudwatch-agent.json /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json && \
	systemctl --now enable amazon-cloudwatch-agent

readonly elasticraft_dir=/srv/elasticraft
# Ensure the data volume mount point exists, and that it has no permissions (to avoid accidental writes if
# the volume isn't attached and mounted).
mkdir --parents $elasticraft_dir && chmod 000 $elasticraft_dir

readonly device=xvdm
/usr/local/sbin/attach-volume $device $instance_id $region
if [ $? -ne 0 ]; then
	echo Failed to attach data volume, terminating instance
	# systemctl poweroff
	exit 1
fi

# Instance types that expose EBS volumes as NVMe devices create the primary device node at /dev/nvme*.
# Sometimes, the /dev/xvd* nodes only appear after a short while. Wait until that happens before completing.
until [ -b /dev/$device ]; do
	echo Waiting for /dev/$device to exist. Checking again in 1 second.
	sleep 1 # inotifywait would be ideal, but Amazon Linux 2 doesn't ship it
done

# Create the Minecraft log file in the system log directory and ensure it will be writeable by the process
readonly minecraft_log_path=/var/log/minecraft.log
touch $minecraft_log_path && chown minecraft: $minecraft_log_path

# Ensure the server is started when the system boots
systemctl enable minecraft enderman@$region rs-comparator@$region

# Ensure that /etc/fstab contains an entry for the data volume mount so that the filesystem will be mounted on
# a reboot.
echo /dev/$device $elasticraft_dir auto auto,_netdev 0 2 >> /etc/fstab

# If a reboot is not required due to no kernel update having been installed, start the Minecraft server
if [ $(uname --kernel-release) == $(rpm --query kernel --queryformat '%{VERSION}-%{RELEASE}.%{ARCH}\n'|sort --version-sort|tail --lines=1) ]; then
	systemctl start minecraft enderman@$region rs-comparator@$region
fi
