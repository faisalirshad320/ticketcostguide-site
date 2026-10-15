<?php
// Serve the static homepage; overrides Cloudways' default placeholder index.php
// so Nginx (which prefers index.php over index.html) returns our real home page.
readfile(__DIR__ . '/index.html');
