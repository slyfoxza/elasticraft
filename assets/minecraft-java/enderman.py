#!/usr/bin/env python3
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
import argparse
import asyncio
import ctypes
from ctypes import c_char_p, c_int, c_uint32
from ctypes.util import find_library
import logging
import os
import re
from struct import Struct
import sys

logging.basicConfig(format="%(message)s", level=logging.WARN)
logger = logging.getLogger("enderman")
logger.setLevel(logging.INFO)

libc = ctypes.CDLL(find_library("c") or "libc.so.6", use_errno=True)
libc.inotify_init1.argtypes = (c_int,)
libc.inotify_add_watch.argtypes = (c_int, c_char_p, c_uint32)
IN_NONBLOCK = 0x800
IN_MODIFY = 0x2

# See struct inotify_event in inotify(7)
INOTIFY_EVENT = Struct("i3I")
INOTIFY_BUFFER_SIZE = INOTIFY_EVENT.size + os.pathconf("/", "PC_NAME_MAX") + 1

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--dry-run", action="store_true")
parser.add_argument("-D", "--debug", action="store_true")
parser.add_argument("-l", "--log-path", default="/var/log/minecraft.log")
parser.add_argument("-n", "--new-server-wait-time", type=int, default=(15 * 60))
parser.add_argument("-w", "--rejoin-wait-time", type=int, default=(5 * 60))
parser.add_argument("-W", "--final-wait-time", type=int, default=5)
arguments = parser.parse_args()

if arguments.debug:
    logger.setLevel(logging.DEBUG)


def libc_check(result: c_int) -> c_int:
    """Wraps a libc result, throwing an OSError if it indicates an error."""
    if result == -1:
        raise OSError(ctypes.get_errno(), os.strerror(ctypes.get_errno()))
    return result


class Enderman:
    LOG_PATTERN = re.compile(": (?!<).* (?P<type>joined|left) the game$")

    def __init__(self):
        self.active_player_count = 0
        self.is_new_server = True
        self.shutdown_task = None

        if arguments.dry_run:
            from unittest.mock import MagicMock

            self.eni_id = "eni-d34db33f"
            self.server_id = "server-id"

            self.ec2 = MagicMock(name="ec2")
            self.ec2.security_groups.filter.return_value = [
                MagicMock(name="SecurityGroup")
            ]

            self.shutdown_system = MagicMock(
                name="shutdown_system", side_effect=lambda: sys.exit(0)
            )
        else:
            import boto3
            import requests

            def imds(token: str, path: str) -> str:
                return requests.get(
                    f"http://169.254.169.254/latest/meta-data/{path}",
                    headers={"X-aws-ec2-metadata-token": token},
                ).text

            token = requests.put(
                "http://169.254.169.254/latest/api/token",
                headers={"X-aws-ec2-metadata-token-ttl-seconds": str(21600)},
            ).text
            region = imds(token, "placement/region")
            self.eni_id = imds(
                token, f"network/interfaces/macs/{imds(token, 'mac')}/interface-id"
            )

            with open("/etc/elasticraft/server-id") as f:
                self.server_id = f.read()

            self.ec2 = boto3.resource("ec2", region_name=region)

            self.shutdown_system = self.systemctl_shutdown_system

    def __enter__(self):
        self.log = open(arguments.log_path)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.log.close()
        self.log = None

    def read_inotify(self):
        # Loop to drain the buffer entirely (until read returns EAGAIN/
        # EWOULDBLOCK)
        try:
            while True:
                # Since we only have one watch, we don't actually care about
                # unpacking the inotify event
                os.read(self.inotify, INOTIFY_BUFFER_SIZE)
        except BlockingIOError:
            pass
        logger.debug("log_modify_event.set()")
        self.log_modify_event.set()

    async def parse_log(self):
        logger.debug("Parsing available log lines")
        while True:
            position = self.log.tell()
            line = self.log.readline()
            if len(line) == 0:
                break
            elif line[-1] != "\n":
                # Didn't read a full line. Reset the stream position, and wait
                # for another write event to come from inotify.
                self.log.seek(position)
                break

            result = self.LOG_PATTERN.search(line)
            if result is not None:
                self.active_player_count += (
                    1 if result.group("type") == "joined" else -1
                )

            if self.is_new_server and self.active_player_count > 0:
                self.is_new_server = False

            # Yield between log lines to avoid starving any other coroutines
            await asyncio.sleep(0)

    async def shutdown(self):
        try:
            # Wait for a longer time in case this is a new server and someone is
            # struggling with DNS propagation, or if the last player
            # disconnected due to a network issue instead of actually leaving.
            # If they reconnect in this period, the task will be cancelled by
            # the check in the main loop.
            if is_new_server:
                await asyncio.sleep(arguments.new_server_wait_time)
                logger.info("New server wait time expired, removing security group")
            else:
                await asyncio.sleep(arguments.rejoin_wait_time)
                logger.info("Rejoin wait time expired, removing security group")

            # Remove the security group that allows ingress to the Minecraft
            # game port. This is to ensure that no new player can connect while
            # the server is actively shutting down.
            groups = list(
                self.ec2.security_groups.filter(
                    Filters=[
                        {"Name": "tag:elasticraft:serverId", "Values": [self.server_id]}
                    ]
                )
            )
            if len(groups) != 1:
                raise RuntimeError("Expected single security group")
            group_to_remove = groups[0]

            eni = self.ec2.NetworkInterface(self.eni_id)
            original_group_ids = [g["GroupId"] for g in eni.groups]
            new_group_ids = set(original_group_ids)
            new_group_ids.discard(group_to_remove.id)
            eni.modify_attribute(Groups=list(new_group_ids))

            # Once the security group is removed, wait for a short time. This
            # is to handle a race condition where a player connects while the
            # ingress security group was being removed, making the server live
            # again. In that case, we need to restore the security group that
            # we removed before re-raising the cancellation signal.
            try:
                await asyncio.sleep(arguments.final_wait_time)
                logger.info("Final wait time expired, shutting down system")
            except asyncio.CancelledError:
                logger.info("Shutdown task cancelled, restoring security group")
                eni.modify_attribute(Groups=original_group_ids)
                raise

            shutdown_system_task = asyncio.create_task(self.shutdown_system())
            await asyncio.shield(shutdown_system_task)
        finally:
            # Indicate to the rest of the program that there is no active
            # shutdown task, no matter how we get to the exit of this function.
            self.shutdown_task = None

    async def systemctl_shutdown_system(self):
        process = await asyncio.create_subprocess_exec(
            "/usr/bin/sudo",
            "/usr/bin/systemctl",
            "--no-ask-password",
            "stop",
            "minecraft",
        )
        if await process.wait() != 0:
            raise RuntimeError("Failed to stop Minecraft service")

        process = await asyncio.create_subprocess_exec(
            "/usr/bin/sudo", "/usr/bin/systemctl", "--no-ask-password", "poweroff"
        )
        if await process.wait() != 0:
            raise RuntimeError

    async def main(self):
        """
        Main loop.

        Enderman uses an event-driven loop to avoid unnecessarily polling the
        Minecraft log file. It integrates with inotify to provide notifications
        of the file being modified, and schedules an asynchronous task to
        shutdown the host when the last player disconnects, based on the
        contents of the Minecraft log file.
        """
        self.inotify = libc_check(libc.inotify_init1(IN_NONBLOCK))
        libc_check(
            libc.inotify_add_watch(self.inotify, arguments.log_path.encode(), IN_MODIFY)
        )

        self.log_modify_event = asyncio.Event()
        asyncio.get_running_loop().add_reader(self.inotify, self.read_inotify)
        while True:
            self.log_modify_event.clear()
            await self.parse_log()

            if self.active_player_count == 0 and self.shutdown_task is None:
                logger.info("Creating shutdown task")
                self.shutdown_task = asyncio.create_task(self.shutdown())
            elif self.active_player_count > 0 and self.shutdown_task is not None:
                logger.info(
                    f"Cancelling shutdown task (active player count {self.active_player_count})"
                )
                self.shutdown_task.cancel()

            # In case we/inotify miss an event, rerun the loop after 30 seconds
            # as a fail-safe.
            try:
                await asyncio.wait_for(self.log_modify_event.wait(), timeout=30)
            except asyncio.exceptions.TimeoutError:
                pass


if __name__ == "__main__":
    with Enderman() as app:
        asyncio.run(app.main())
