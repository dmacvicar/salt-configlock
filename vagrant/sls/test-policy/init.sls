/etc/test-directory:
  file.directory:
    - makedirs: True

/etc/test-config-file:
  file.managed:
    - source: salt://test-policy/test-config-file


