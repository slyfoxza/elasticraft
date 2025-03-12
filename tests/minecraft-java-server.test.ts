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
import { rm } from "node:fs/promises";

import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { App, Stack } from "aws-cdk-lib";
import { Match, Template } from "aws-cdk-lib/assertions";
import * as ec2 from "aws-cdk-lib/aws-ec2";

import { MinecraftJavaServer } from "../src/minecraft-java-server.js";

describe(MinecraftJavaServer, () => {
  let stack: Stack;

  beforeEach(() => {
    stack = new Stack();
  });

  afterEach(async () => {
    const outputDirectory = App.of(stack)?.outdir;
    if (outputDirectory !== undefined) {
      await rm(outputDirectory, { recursive: true });
    }
  });

  it("generates the expected template", () => {
    new MinecraftJavaServer(stack, "Test");
    expect(Template.fromStack(stack).toJSON()).toMatchSnapshot();
  });

  it("accepts a different instance type", () => {
    new MinecraftJavaServer(stack, "Test", {
      instanceType: ec2.InstanceType.of(
        ec2.InstanceClass.C7I,
        ec2.InstanceSize.LARGE,
      ),
    });
    const template = Template.fromStack(stack);
    template.hasResourceProperties("AWS::EC2::LaunchTemplate", {
      LaunchTemplateData: { InstanceType: "c7i.large" },
    });
  });

  it("accepts a custom server ID", () => {
    new MinecraftJavaServer(stack, "Test", { serverId: "my-server" });
    const template = Template.fromStack(stack);
    const serverIdTag = { Key: "elasticraft:serverId", Value: "my-server" };
    template.hasResourceProperties("AWS::EC2::LaunchTemplate", {
      LaunchTemplateData: {
        TagSpecifications: [
          { ResourceType: "instance", Tags: Match.arrayWith([serverIdTag]) },
          { ResourceType: "volume", Tags: Match.arrayWith([serverIdTag]) },
        ],
      },
      TagSpecifications: [
        {
          ResourceType: "launch-template",
          Tags: Match.arrayWith([serverIdTag]),
        },
      ],
    });
  });
});
