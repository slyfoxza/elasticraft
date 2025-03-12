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
import { Tags } from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import { Construct } from "constructs";

export interface MinecraftJavaServerProps {
  /**
   * The [EC2 instance type](https://aws.amazon.com/ec2/instance-types/) to
   * launch the server on. Since Amazon Linux AMIs and Java runtimes are
   * available for the ARM architecture, Graviton instances are a suitable
   * choice which can lower the cost of running the server.
   *
   * @default "t4g.medium"
   */
  instanceType?: ec2.InstanceType;

  /**
   * The _server ID_ for the server instance this construct manages. This
   * identifier is used at deployment time to tag resources, and at runtime to
   * dynamically discover those resources and distinguish them from sibling
   * resources that may belong to a different server instance.
   *
   * The server ID is also used to discover resources managed outside of the CDK
   * and CloudFormation lifecycle, such as the persistent data volume where game
   * data is stored.
   *
   * If not specified, the {@link MinecraftJavaServer} construct ID will be used.
   */
  serverId?: string;
}

/**
 * Construct providing resources used to run a Minecraft: Java Edition server.
 */
export class MinecraftJavaServer extends Construct {
  /**
   * Launch template that may be used with
   * [RunInstances](https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_RunInstances.html)
   * to start the Minecraft server instance.
   */
  readonly launchTemplate: ec2.ILaunchTemplate;

  constructor(scope: Construct, id: string, props?: MinecraftJavaServerProps) {
    super(scope, id);
    const serverId = props?.serverId ?? id;

    const instanceType =
      props?.instanceType ??
      ec2.InstanceType.of(ec2.InstanceClass.T4G, ec2.InstanceSize.MEDIUM);
    this.launchTemplate = new ec2.LaunchTemplate(this, "LaunchTemplate", {
      httpTokens: ec2.LaunchTemplateHttpTokens.REQUIRED,
      instanceInitiatedShutdownBehavior:
        ec2.InstanceInitiatedShutdownBehavior.TERMINATE,
      instanceType,
      machineImage: ec2.MachineImage.resolveSsmParameterAtLaunch(
        ec2.AmazonLinux2023ImageSsmParameter.ssmParameterName({
          cpuType:
            instanceType.architecture as unknown as ec2.AmazonLinuxCpuType,
        }),
      ),
      requireImdsv2: true,
    });
    Tags.of(this.launchTemplate).add("elasticraft:serverId", serverId);
  }
}
