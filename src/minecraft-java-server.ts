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
import path from "node:path";

import { Stack, Tags } from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as iam from "aws-cdk-lib/aws-iam";
import * as logs from "aws-cdk-lib/aws-logs";
import { Asset } from "aws-cdk-lib/aws-s3-assets";
import { Construct } from "constructs";
import * as YAML from "yaml";

import { TagKeys } from "./tags.js";

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
   * The role associated with the instance profile for the server.
   */
  readonly role: iam.IRole;

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

    this.role = new iam.Role(this, "Role", {
      assumedBy: new iam.ServicePrincipal("ec2.amazonaws.com"),
    });

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
    Tags.of(gameSecurityGroup).add(TagKeys.ServerId, this.serverId);

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
      role: this.role,
      securityGroup: gameSecurityGroup,
      userData: this.renderUserData(),
    });
    Tags.of(this.launchTemplate).add(TagKeys.ServerId, this.serverId);
    this.launchTemplate.addSecurityGroup(this.generalSecurityGroup);

    const cloudInitLogGroup = new logs.LogGroup(this, "CloudInitLogGroup", {
      logGroupName: `${this.serverId}/cloud-init-output.log`,
      retention: logs.RetentionDays.ONE_MONTH,
    });
    const minecraftLogGroup = new logs.LogGroup(this, "MinecraftLogGroup", {
      logGroupName: `${this.serverId}/minecraft.log`,
      retention: logs.RetentionDays.ONE_MONTH,
    });

    this.grantRolePermissions({
      logGroups: [cloudInitLogGroup, minecraftLogGroup],
    });
  }

  private renderUserData(): ec2.UserData {
    const asset = new Asset(this, "UserDataAsset", {
      path: path.join(import.meta.dirname, "../assets/minecraft-java"),
      readers: [this.role],
    });

    const userData = new ec2.MultipartUserData();
    userData.addUserDataPart(
      ec2.UserData.custom(
        YAML.stringify({
          users: [
            "default",
            {
              name: "minecraft",
              homedir: "/srv/minecraft",
              no_create_home: true,
              no_user_group: true,
              primary_group: "games",
              shell: "/sbin/nologin",
              system: true,
              uid: 25_565,
            },
          ],
        }),
      ),
      'text/cloud-config; charset="utf-8"',
    );
    userData.addUserDataPart(
      ec2.UserData.forLinux(),
      ec2.MultipartBody.SHELL_SCRIPT,
      true,
    );
    const downloadedAsset = userData.addS3DownloadCommand({
      bucket: asset.bucket,
      bucketKey: asset.s3ObjectKey,
      localFile: "/tmp/elasticraft/cloud-init.zip",
    });
    userData.addCommands(
      "mkdir --parents /etc/elasticraft",
      `echo -n '${this.serverId}' > /etc/elasticraft/server-id`,
      `cd $(dirname '${downloadedAsset}')`,
      `unzip ${downloadedAsset}`,
    );
    userData.addExecuteFileCommand({ filePath: "./cloud-init.sh" });
    return userData;
  }

  private grantRolePermissions({ logGroups }: { logGroups: logs.LogGroup[] }) {
    for (const lg of logGroups) lg.grantWrite(this.role);

    this.role.addToPrincipalPolicy(
      new iam.PolicyStatement({
        actions: [
          // Needed by CloudWatch Agent
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams",
          // Needed by attach-volume.py
          "ec2:DescribeVolumes",
        ],
        resources: ["*"],
      }),
    );
    this.role.addToPrincipalPolicy(
      /* Needed by attach-volume.py: only allow it to attach the data volume
       * for this server */
      new iam.PolicyStatement({
        actions: ["ec2:AttachVolume"],
        resources: [
          Stack.of(this).formatArn({
            service: "ec2",
            resource: "volume",
            resourceName: "*",
          }),
        ],
        conditions: {
          StringEquals: {
            "aws:ResourceTag/elasticraft:serverId": this.serverId,
            "aws:ResourceTag/elasticraft:volumeType": "data-volume",
          },
        },
      }),
    );
    this.role.addToPrincipalPolicy(
      /* Needed by attach-volume.py: only allow it to attach the data volume to
       * this server's instance */
      new iam.PolicyStatement({
        actions: ["ec2:AttachVolume"],
        resources: [
          Stack.of(this).formatArn({
            service: "ec2",
            resource: "instance",
            resourceName: "*",
          }),
        ],
        conditions: {
          StringEquals: {
            "aws:ResourceTag/elasticraft:serverId": this.serverId,
          },
        },
      }),
    );
  }
}
