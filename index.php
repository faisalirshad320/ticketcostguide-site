<?php
// Nginx on Cloudways sends every request it cannot match to a file here
// (try_files ... /index.php). Serve the static homepage only for "/";
// anything else is a genuinely missing page and must return 404, or Google
// indexes copies of the homepage under random URLs.
$path = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/';
if ($path === '/' || $path === '/index.php') {
    readfile(__DIR__ . '/index.html');
    exit;
}
http_response_code(404);
header('X-Robots-Tag: noindex');
$page = __DIR__ . '/404.html';
if (is_file($page)) { readfile($page); exit; }
echo '<!doctype html><meta charset="utf-8"><title>Page not found</title><h1>Page not found</h1><p><a href="/">TicketCostGuide home</a></p>';
