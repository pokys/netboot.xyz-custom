# Dočasné Alpine appliances

V **Live tools → Alpine Live - App appliances** zaškrtni jednu nebo více aplikací.
Položka se každým výběrem přepne mezi `[-]` a `[x]`. Potom zvol **Continue**,
větev **Alpine 3.24 / Latest stable** a **DHCP / Static IPv4**.
Prázdný výběr připraví jen původní Docker + Dockge + SSH.

Společný základ zjednodušuje údržbu i kombinování aplikací. Nextcloud je zde
oficiální Docker image na Alpine hostu, nikoli nativní instalace z Alpine APK.
Proxmox community scripts byly inspirací pro výběr aplikací; jejich LXC instalátory
se při bootu nestahují ani nespouštějí.

Všechno běží v RAM: systém, images, databáze, uživatelská data i hesla.
Žádný fyzický disk se nevybírá ani automaticky nepřipojuje.
Restart smaže celé prostředí. Zvolené kombinace jsou určeny pro dočasný lab na důvěryhodné síti.

| Aplikace | Adresa | První přístup / použití |
| --- | --- | --- |
| Dockge | `http://IP:5001` | vytvoření účtu při prvním otevření, správa všech stacků |
| Nextcloud | `http://IP:8080` | `admin`, soubory a spolupráce; vlastní PostgreSQL a Redis |
| Copyparty | `http://IP:3923` | `admin`, upload/download; zápis na RAM disk výslovně povolen přepínačem `--wram` |
| Wastebin | `http://IP:8088` | `admin`, HTTP Basic Auth přes Caddy; vlastní SQLite |
| Semaphore UI | `http://IP:3000` | `admin`, Ansible a další automatizace; SQLite |
| Caddy | `http://IP:8081` | `admin`, HTTP Basic Auth, statický web / upravitelná reverse proxy |
| Uptime Kuma | `http://IP:3001` | vytvoření účtu při prvním otevření; monitory přidáváš ručně |
| Apache Guacamole | `http://IP:8082/guacamole/` | `guacadmin`, RDP/VNC/SSH připojení přidáváš ručně |
| IT-Tools | `http://IP:8083` | bez účtu, převody textu, JSON, IP adresy a jiné browserové utility |

Heslo předvytvořených aplikačních účtů je stejné **náhodné osmiznakové heslo jako pro SSH**,
zobrazené na konzoli. Vzniká znovu při každém bootu. Databázová hesla a šifrovací klíč
Semaphore se generují zvlášť, mají vyšší délku a uživatel je nemusí přepisovat.
V repozitáři ani v overlayi nejsou uložená hesla. Runtime `.env` soubory mají práva 0600.
Guacamole dostane vlastní schéma databáze a změněné heslo ještě před spuštěním webu;
upstream `guacadmin/guacadmin` se nepoužívá. guacd ani databáze nepublikují porty do LAN.

## Paměť a start

Pro lehčí výběr doporučuji **8 GB RAM**, pro všechny služby současně **16 GB RAM**.
Nextcloud, Guacamole a Semaphore mají výrazně větší images než malý file server.
Celý výběr při ověřeném bootu spotřeboval přibližně 8 GB RAM filesystemu včetně Docker images.
Zbývající místo je zároveň kapacitou pro uploady, databáze a kontejnery; data nejsou na disku.
Paměťové limity kontejnerů omezují procesy, nikoli velikost uploadů v hostitelském tmpfs.

Při prvním bootu se images stahují přímo od jejich vydavatelů. Všechny jsou připnuté
na konkrétní SHA256 digest v Compose šablonách, včetně obrazů označených tagem `latest`.
Výpis zdrojů je v [catalog/appliance-images.json](../catalog/appliance-images.json).
Na našem GitHubu je pouze vlastní konfigurace a malý Alpine overlay; Docker images se nerepublikují.

Dockge a SSH startují před aplikacemi. Stacky se spouštějí postupně a chyba jedné služby
nezastaví další vybrané aplikace. První inicializace Nextcloudu a Guacamole může trvat několik minut.
Úspěch znamená dostupné aplikační rozhraní; u Nextcloudu také dokončenou instalaci,
u Semaphore a Guacamole úspěšné přihlášení, u Caddy/Wastebin přístup přes autentizaci.

## Správa po bootu

Každý stack je v `/opt/stacks/NAZEV/compose.yaml` a je dostupný v Dockge.
Jeho `.env`, konfigurační soubory a Docker volumes zůstávají jen v RAM.
`live-apps` nepřepisuje již připravenou Compose konfiguraci ani existující `.env`.

```sh
live-apps status
live-apps start copyparty,wastebin
live-apps stop wastebin
tail -n 80 /var/log/live-apps.log
docker compose --project-directory /opt/stacks/nextcloud logs --tail 50
```

`stop` zastaví stack, ale nesmaže jeho volumes; při opětovném startu v témže bootu
jsou data zachovaná. Restart stroje je smaže.
Zadání neznámé aplikace se odmítne před změnou kteréhokoliv stacku.

Caddy má při prvním startu autentizovaný ukázkový web v `/opt/stacks/caddy/www/`.
Pro vlastní reverse proxy uprav `/opt/stacks/caddy/Caddyfile` v Dockge nebo přes SSH:
ve stávajícím bloku `:80` ponech `basic_auth` a nahraď `root` a `file_server`
direktivou například `reverse_proxy host.docker.internal:3001`. Pak reload:

```sh
docker compose --project-directory /opt/stacks/caddy exec caddy caddy reload --config /etc/caddy/Caddyfile
```

Výchozí konfigurace používají HTTP na uvedených portech. Automatické veřejné HTTPS
potřebuje vlastní doménu, DNS a dostupné porty; u dočasného stroje se certifikáty po restartu také ztratí.
Nextcloud důvěřuje při přípravě pouze aktuálním IPv4 adresám hostu, localhost a hostname;
případný další název reverse proxy doplň do jeho `trusted_domains`.

## Ověření a údržba

```text
python tools/build_alpine_overlay.py
python tools/build_alpine_overlay.py --check
python -m unittest discover -s tests -v
```

Aktualizace image vyžaduje změnu digestu v šabloně a katalogu, rebuild overlaye a nový runtime test.
Ověření v diskless QEMU s 16 GB RAM zahrnuje start všech osmi aplikací současně,
přihlášení do Nextcloudu, Copyparty, Semaphore a Guacamole, upload/download přes
Nextcloud WebDAV a Copyparty, vytvoření/načtení paste ve Wastebinu, Basic Auth Caddy,
odmítnutí výchozího hesla Guacamole, web Uptime Kuma a IT-Tools, privátní práva credentials
a odmítnutí neznámého výběru. Runtime kontrola je v `tests/vm/appliance-smoke.sh`
a spouští se uvnitř takového testovacího VM po startu všech aplikací; zapisuje testovací data.
K ověření Docker vrstvy se používá lokální HTTP kopie stejného overlaye a oficiální Alpine kernel/initramfs.
Samostatný test s netboot.xyz iPXE ověřil zaškrtnutí dvou aplikací, předání jejich seznamu
a vymazání výběru s předáním `none`; finální chain byl v tomto testu nahrazen lokálním kontrolním endpointem.
Ověřeno je i pokračování dalšího stacku po chybné konfiguraci předchozího a zachování
uživatelské Compose úpravy, credentials a dat při restartu stacku v témže bootu.
Další boot se 4 GB RAM, pevnou větví Alpine 3.24 a prázdným výběrem spustil pouze
Docker/Dockge/SSH; předchozí stacky, volumes a testovací soubor zmizely a heslo vzniklo znovu.
Úplný řetězec firmware → menu → veřejné CDN, Secure Boot a reálné RDP/VNC relace nejsou ověřené.

Další rozumné kandidáty pro pozdější rozšíření vidím v **OpenSpeedTest** pro měření
propustnosti LAN a **Syncthing** pro dočasné předání dat mezi stroji. Syncthing bych
nepřidával do automatického výběru bez rozhodnutí o párování a směru synchronizace.

## Primární zdroje

- [Nextcloud Docker](https://github.com/nextcloud/docker)
- [Copyparty Docker a konfigurace](https://github.com/9001/copyparty/tree/hovudstraum/scripts/docker)
- [Wastebin](https://github.com/matze/wastebin)
- [Semaphore Docker](https://semaphoreui.com/docs/admin-guide/installation/docker)
- [Caddy Docker](https://hub.docker.com/_/caddy)
- [Uptime Kuma](https://github.com/louislam/uptime-kuma)
- [Apache Guacamole Docker](https://guacamole.apache.org/doc/gug/guacamole-docker.html)
- [Guacamole databázové schéma a hash hesla](https://guacamole.apache.org/doc/gug/jdbc-auth-schema.html)
- [IT-Tools](https://github.com/CorentinTh/it-tools)
- [Community scripts: Alpine Nextcloud](https://github.com/community-scripts/ProxmoxVE/blob/main/install/alpine-nextcloud-install.sh)
- [Community scripts: Apache Guacamole](https://github.com/community-scripts/ProxmoxVE/blob/main/install/apache-guacamole-install.sh)
