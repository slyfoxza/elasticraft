/* Copyright 2025 Philip Cronje
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not
 * use this file except in compliance with the License. You may obtain a copy of
 * the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations under
 * the License.
 */
import * as ec2 from "aws-cdk-lib/aws-ec2";
import { Construct } from "constructs";

export interface MinecraftJavaServerProps {
  instanceType?: ec2.InstanceType;
}

export class MinecraftJavaServer extends Construct {
  readonly launchTemplate: ec2.ILaunchTemplate;

  constructor(scope: Construct, id: string, props?: MinecraftJavaServerProps) {
    super(scope, id);

    const instanceType =
      props?.instanceType ??
      ec2.InstanceType.of(ec2.InstanceClass.T4G, ec2.InstanceSize.MEDIUM);
    this.launchTemplate = new ec2.LaunchTemplate(this, "LaunchTemplate", {
      instanceType,
      machineImage: ec2.MachineImage.resolveSsmParameterAtLaunch(
        ec2.AmazonLinux2023ImageSsmParameter.ssmParameterName({
          cpuType:
            instanceType.architecture as unknown as ec2.AmazonLinuxCpuType,
        }),
      ),
    });
  }
}
