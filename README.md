
*EXPERIMENTAL, DON'T USE THIS*

# Saltstack beacon to protect managed files

## Development

For comfortable development, add the git checkout

```yaml
module_dirs:
  - /yourgit/salt-configlock
```

Refresh the modules with

```
salt-call saltutil.sync_modules
```

You can test that the events are passed by calling on the master:

```
salt-run state.event pretty=true
```

## Configuration

```yaml
beacons:
  configlock:
    managed:
      lock: True
```

## Author

* Duncan Mac-Vicar P. <dmacvicar@suse.de>

## License

Copyright 2015 SUSE LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

 http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.


