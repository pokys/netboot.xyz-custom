set -eu
p=$(cat /run/docker-live/ssh-password)
printf 'appliance-probe' > /tmp/appliance-probe.txt
curl -fsS -u "admin:$p" -T /tmp/appliance-probe.txt http://127.0.0.1:8080/remote.php/dav/files/admin/appliance-probe.txt >/dev/null
test "$(curl -fsS -u "admin:$p" http://127.0.0.1:8080/remote.php/dav/files/admin/appliance-probe.txt)" = appliance-probe
echo 'PASS Nextcloud admin authentication + WebDAV upload/download'
curl -fsS -u "admin:$p" -T /tmp/appliance-probe.txt http://127.0.0.1:3923/appliance-probe.txt >/dev/null
test "$(curl -fsS -u "admin:$p" http://127.0.0.1:3923/appliance-probe.txt)" = appliance-probe
echo 'PASS Copyparty authenticated upload/download'
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8088/)" = 401
payload=$(curl -fsS -u "admin:$p" -H 'Content-Type: application/json' -d '{"text":"appliance-probe","expires":3600}' http://127.0.0.1:8088/)
path=$(printf '%s' "$payload" | sed -n 's/.*"path":"\([^"]*\)".*/\1/p')
test "$(curl -fsS -u "admin:$p" "http://127.0.0.1:8088/raw$path")" = appliance-probe
echo 'PASS Wastebin authentication + paste create/read'
curl -fsS -c /tmp/semaphore-cookies -H 'Content-Type: application/json' -d "{\"auth\":\"admin\",\"password\":\"$p\"}" http://127.0.0.1:3000/api/auth/login >/dev/null
curl -fsS -b /tmp/semaphore-cookies http://127.0.0.1:3000/api/user | grep -q 'admin'
echo 'PASS Semaphore admin login + authenticated API'
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8081/)" = 401
curl -fsS -u "admin:$p" http://127.0.0.1:8081/ | grep -q 'Temporary Caddy'
echo 'PASS Caddy authenticated static site'
curl -fsSL http://127.0.0.1:3001/ | grep -qi 'uptime kuma'
echo 'PASS Uptime Kuma web application'
curl -fsS --data-urlencode username=guacadmin --data-urlencode "password=$p" http://127.0.0.1:8082/guacamole/api/tokens | grep -q 'authToken'
test "$(curl -s -o /dev/null -w '%{http_code}' -d 'username=guacadmin&password=guacadmin' http://127.0.0.1:8082/guacamole/api/tokens)" != 200
echo 'PASS Guacamole login + upstream default password rejected'
curl -fsS http://127.0.0.1:8083/ | grep -qi 'IT.Tools'
echo 'PASS IT-Tools web application'
before=$(docker ps -q | sort)
set +e
live-apps start 'copyparty,unlisted' >/dev/null 2>&1
code=$?
set -e
test "$code" = 2
test "$(docker ps -q | sort)" = "$before"
echo 'PASS invalid application selection rejected without changing containers'
test "$(stat -c %a /opt/stacks/nextcloud/.env)" = 600
test "$(stat -f -c %T /)" = tmpfs
echo 'PASS runtime credentials are private and root filesystem is RAM'
env_before=$(sha256sum /opt/stacks/copyparty/.env)
printf '\n# User customization preserved by live-apps\n' >> /opt/stacks/copyparty/compose.yaml
live-apps start copyparty >/dev/null 2>&1
test "$(sha256sum /opt/stacks/copyparty/.env)" = "$env_before"
grep -q 'User customization preserved' /opt/stacks/copyparty/compose.yaml
test "$(curl -fsS -u "admin:$p" http://127.0.0.1:3923/appliance-probe.txt)" = appliance-probe
echo 'PASS restarting a stack preserves credentials, user configuration and data within this boot'
