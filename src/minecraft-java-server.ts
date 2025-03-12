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

  /**
   * The port the server will listen on. Used to setup a security group with
   * ingress rules.
   *
   * @default 25565
   */
  serverPort?: ec2.Port;

  /**
   * The VPC the server instance will run in.
   */
  vpc: ec2.IVpc;
}

/**
 * Construct providing resources used to run a Minecraft: Java Edition server.
 */
export class MinecraftJavaServer extends Construct {
  /**
   * General-purpose security group that will be associated to the server
   * instance. By default, this security group only provides egress rules.
   * Further customization is possible by interacting with this property,
   * however.
   */
  readonly generalSecurityGroup: ec2.ISecurityGroup;

  /**
   * Launch template that may be used with
   * [RunInstances](https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_RunInstances.html)
   * to start the Minecraft server instance.
   */
  readonly launchTemplate: ec2.LaunchTemplate;

  /**
   * The _server ID_ for the server instance this construct manages. This will
   * either be the value supplied in the `props` during construction, or will be
   * the construct ID.
   *
   * @see {@link MinecraftJavaServerProps.serverId}
   */
  readonly serverId: string;

  constructor(scope: Construct, id: string, props: MinecraftJavaServerProps) {
    super(scope, id);
    this.serverId = props.serverId ?? id;

    this.generalSecurityGroup = new ec2.SecurityGroup(
      this,
      "GeneralSecurityGroup",
      {
        allowAllIpv6Outbound: true,
        allowAllOutbound: true,
        vpc: props.vpc,
      },
    );

    /* The game security group provides ingress rules for the Minecraft server
     * port. During the server's automatic shutdown sequence, this security
     * group will be removed from the instance network interface to ensure the
     * shutdown only proceeds if no player can join halfway through the instance
     * terminating. */
    const gameSecurityGroup = new ec2.SecurityGroup(this, "GameSecurityGroup", {
      allowAllIpv6Outbound: false,
      allowAllOutbound: false,
      vpc: props.vpc,
    });
    const serverPort = props.serverPort ?? ec2.Port.tcp(25_565);
    gameSecurityGroup.addIngressRule(ec2.Peer.anyIpv4(), serverPort);
    gameSecurityGroup.addIngressRule(ec2.Peer.anyIpv6(), serverPort);
    Tags.of(gameSecurityGroup).add("elasticraft:serverId", this.serverId);

    const instanceType =
      props.instanceType ??
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
      securityGroup: gameSecurityGroup,
      userData: this.renderUserData(),
    });
    Tags.of(this.launchTemplate).add("elasticraft:serverId", this.serverId);
    this.launchTemplate.addSecurityGroup(this.generalSecurityGroup);
  }

  private renderUserData(): ec2.UserData {
    const userData = new ec2.MultipartUserData();
    userData.addUserDataPart(
      ec2.UserData.forLinux(),
      ec2.MultipartBody.SHELL_SCRIPT,
      true,
    );
    userData.addCommands(
      "mkdir --parents /etc/elasticraft",
      `echo -n '${this.serverId}' > /etc/elasticraft/server-id`,
    );
    return userData;
  }
}
