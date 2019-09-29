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
.PHONY: all clean

all: server_post.zip snapshot_on_shutdown.zip

clean:
	$(RM) server_post.zip snapshot_on_shutdown.zip

pip-install.timestamp: requirements.txt
	$(RM) -r lambda-dependencies && mkdir -p lambda-dependencies
	pip3 install -r $< -t lambda-dependencies --no-compile --no-deps && touch $@

%.zip: %.py pip-install.timestamp
	$(RM) $@ && zip -9 -ll $@ $< && \
		cd lambda-dependencies && \
		zip -9 -r ../$@ . -x bin/ bin/* *.dist-info/ *.dist-info/*

%.py.zip: %.py
	$(RM) $@ && zip -9 -ll $@ $<
