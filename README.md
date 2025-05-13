# Elasticraft

Provides a [CDK constructs][] library which can be used to operate an _elastic [Minecraft][] server instance_, using [Amazon EC2][] for the compute capacity.

## y tho

The use case Elasticraft is designed for is that of a private Minecraft server that is mostly idle over a period of a day.
Typically, a server like this would be hosted either from a home connection (which is not always ideal or feasible), or from always-on (and thus, always-billed) compute capacity, such as a VPS or other cloud instance.
Given the usage pattern where play happens in bursts of activity (after work, or weekends, for example), paying for unused compute capacity is financially inefficient.

Elasticraft provides simple elasticity for this use case, taking advantage of the ["only pay for what you use"][AWS Pricing] nature of cloud pricing.
Using Elasticraft, a server may be started up on-demand, and also supports automatic shutdown when it detects that the Minecraft server has become idle, ensuring the instance doesn't continue racking up hours for nothing.

## Supported servers

* Minecraft: Java Edition

## How it works

Integrating an Elasticraft server construct in a [CDK application][] will provide a launch template that may be used to launch an instance with the necessary on-host configuration and software for an elastic game server.
The launch template contains [user data][EC2 user data] that allows the instance to configure itself without any additional external dependencies or software repositories.
Minecraft server data is stored on a persistent data volume that is dynamically attached to a running instance, and detached upon instance termination.

One of the software components run on each instance is a daemon that detects when the server has gone idle (that is, the last player has disconnected) and schedules an automatic shutdown of the instance. If a player connects before the shutdown is initiated, the shutdown will be cancelled.

## Integrating Elasticraft

At the moment, Elasticraft is _not_ published to the npm package repository.
Instead, it is currently intended to be consumed as a [Git submodule][].

```sh
git submodule add https://github.com/slyfoxza/elasticraft.git
```

In the consuming `package.json`, add it as a `file:` dependency:

```json
"dependencies": {
  "elasticraft": "file:elasticraft"
}
```

Then, instantiate it in a stack like any other construct:

```ts
new MinecraftJavaServer(this, "MinecraftJavaServer", {
  // ...props...
});
```

## License

Elasticraft is made available under the terms of the Apache License 2.0.
See the contents of the LICENSE file for details.

[Amazon EC2]: https://aws.amazon.com/ec2/
[AWS Pricing]: https://aws.amazon.com/pricing/
[CDK application]: https://docs.aws.amazon.com/cdk/v2/guide/apps.html
[CDK constructs]: https://docs.aws.amazon.com/cdk/v2/guide/constructs.html
[EC2 user data]: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/user-data.html
[Git submodule]: https://git-scm.com/book/en/v2/Git-Tools-Submodules
[Minecraft]: https://www.minecraft.net/
[RunInstances]: https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_RunInstances.html
