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

all: api_authorizer.zip python_dependency_layer.zip server_post.py.zip snapshot_on_shutdown.py.zip

clean:
	$(RM) api_authorizer.zip python_dependency_layer.zip server_post.py.zip snapshot_on_shutdown.py.zip
	$(RM) -r pip-install.timestamp requirements.out api_authorizer-requirements.out

pip-install.timestamp: requirements.txt api_authorizer-requirements.txt
	$(RM) -r $(basename $<).out && mkdir -p $(basename $<).out/python && pip3 install -r $< -t $(basename $<).out/python --no-compile --no-deps
	for req in $(basename $(wordlist 2, $(words $?), $?)); do \
		$(RM) -r $$req.out && mkdir -p $$req.out; \
		pip3 install -r $$req.txt -t $$req.out --no-compile --no-deps; \
		[ $$? -eq 0 ] || exit 1; \
	done
	touch $@

python_dependency_layer.zip: pip-install.timestamp
	$(RM) $@ && cd requirements.out && zip -9 -r ../$@ . -x bin/ bin/* *.dist-info/ *.dist-info/*; \

%.zip: %.py pip-install.timestamp
	$(RM) $@ && zip -9 -ll $@ $<
	if [ -d $(basename $<)-requirements.out ]; then \
		cd $(basename $<)-requirements.out && zip -9 -r ../$@ . -x bin/ bin/* *.dist-info/ *.dist-info/*; \
	fi

%.py.zip: %.py
	$(RM) $@ && zip -9 -ll $@ $<
