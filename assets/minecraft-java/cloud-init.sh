#!/bin/bash
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
set -o errexit -o pipefail

# Get the CloudWatch Agent up as soon as possible to get cloud-init logs into
# CloudWatch
dnf --assumeyes install amazon-cloudwatch-agent jq
jq "walk(if type == \"string\" then gsub(\"%serverId%\"; \"$(</etc/elasticraft/server-id)\") else . end)" \
  amazon-cloudwatch-agent.json > \
  /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
systemctl enable --now amazon-cloudwatch-agent
