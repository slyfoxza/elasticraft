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
import { beforeEach, describe, expect, it } from "vitest";

import { Stack } from "aws-cdk-lib";
import { Template } from "aws-cdk-lib/assertions";
import * as ec2 from "aws-cdk-lib/aws-ec2";

import { MinecraftJavaServer } from "../src/minecraft-java-server.js";

describe(MinecraftJavaServer, () => {
  let stack: Stack;

  beforeEach(() => {
    stack = new Stack();
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
});
