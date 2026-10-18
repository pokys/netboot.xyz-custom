# TrueNAS Community Edition installer

V menu vyber **Storage / NAS → TrueNAS Community Edition - Installer** a potom
**Start TrueNAS installer - DHCP**. Přidaná je stabilní verze **25.10.7** pro x86_64
a samostatná volba sériové konzole 115200 baud.

iPXE stáhne kernel a připravený initramfs. Debian live-boot potom přes DHCP stáhne
celé oficiální ISO (2 339 317 760 bajtů) do RAM a spustí interaktivní instalátor.
Pro tento síťový start počítej alespoň s **8 GB RAM**, doporučeno **12 GB**.
TrueNAS potřebuje samostatný systémový disk a další disky pro data. Cílový disk
vybíráš a jeho přepsání potvrzuješ až v instalátoru. Menu nepředává automatickou instalaci.

## Bootovací soubory

Výchozí adresář připravených souborů je GitHub Release tohoto repozitáře:

```text
https://github.com/pokys/netboot.xyz-custom/releases/download/truenas-25.10.7-netboot-v2
```

Obsahuje `truenas-vmlinuz`, `truenas-initrd`, `SHA256SUMS` a `source.json`.
Kernel zůstává beze změn. Initramfs navíc používá `curl`, jeho knihovny a důvěryhodné
CA certifikáty ze stejného ověřeného ISO. Původní BusyBox `wget` se s oficiálním
download serverem nedohodl na TLS a start končil v nouzovém shellu.
Downloader ověřuje certifikát serveru; při chybě stahování boot zastaví.
Knihovny jsou oddělené v `/opt/truenas-netboot`; BusyBox se nemění.
Initramfs obsahuje také malý hook
[`truenas/netboot-media`](../truenas/netboot-media), který v dočasném kořeni
instalátoru upraví `mount-cd`: ISO stažené live-bootem připojí pouze pro čtení
do `/cdrom`. Původní skript hledá jen fyzická média a síťově stažené ISO nenajde.
Zachovává se původní initramfs pořadí úklidových skriptů včetně udev.
Obsah instalovaného systému ani oficiální ISO se nemění.

Volba **Set boot assets / ISO URLs** umožňuje použít HTTP(S) server v LAN.
Zadej adresář se dvěma bootovacími soubory a úplnou URL stejného ISO 25.10.7.
ISO URL musí končit `.iso`, jak vyžaduje Debian live-boot.
Linux získává síť z DHCP znovu; statická konfigurace Alpine se zde nepoužívá.
Parametr `ip=dhcp` se nepředává: tato verze live-boot jej chybně považuje
za statickou IP. Bez něj live-boot automaticky použije DHCP.

## Reprodukovatelná příprava

S Pythonem 3 a 7-Zip spusť do nového výstupního adresáře:

```text
python tools/prepare_truenas.py --output artifacts/truenas-25.10.7 --seven-zip "C:\Program Files\7-Zip\7z.exe"
```

Případně přidej `--iso cesta/TrueNAS-SCALE-25.10.7.iso`, pokud už ISO máš.
Před extrakcí se ověřuje celý obraz proti oficiálnímu SHA256:

```text
54ce9441ce66966a392e28f63604ca3c2c083d0bec4db7bb5af2f74f7a007c8e
```

Při aktualizaci změň verzi, URL a hash v nástroji i menu, znovu připrav assets
a ověř boot i dostupnost `/cdrom/TrueNAS-SCALE.update` před instalací.
Velké binární soubory se ukládají do Release nebo na HTTP server, nikoli do Gitu.

## Rozsah ověření

Ověřeno 19. října 2026: úplné ISO proti oficiálnímu SHA256, jeho GRUB konfigurace,
Debian live-boot podpora `fetch=` pro ISO, původní skript `mount-cd`, příprava
kernelu a upraveného initramfs a automatické testy integrity hooku a menu.
Samostatná GitHub Action [test-truenas.yml](../.github/workflows/test-truenas.yml)
spouští dočasnou VM s DHCP a stažením ISO přes oficiální HTTPS URL.
Úspěch vyžaduje dosažení interaktivní nabídky `Console Setup` / `Install/Upgrade`;
nepřipojuje žádné disky a neprovádí instalaci. Původní v1 v ní reprodukovatelně
selhala při TLS handshake. [Opravená v2 prošla](https://github.com/pokys/netboot.xyz-custom/actions/runs/39175133472)
19. října 2026: QEMU BIOS, 8 GB RAM, DHCP, stažení celého ISO přes HTTPS,
úspěšné `mount-cd.service` a skutečná nabídka `TrueNAS 25.10.7 Console Setup`
s položkou `Install/Upgrade` v sériovém logu.
Instalace na disk, úplný iPXE start, UEFI a Secure Boot zatím nejsou ověřené.
iPXE ani live-boot za běhu automaticky neověřují ISO proti připnutému SHA256;
kontrola se provádí při přípravě bootovacích souborů.

## Oficiální zdroje

- [Stažení TrueNAS a publikovaný SHA256](https://www.truenas.com/download/)
- [Oficiální ISO 25.10.7](https://download.sys.truenas.net/TrueNAS-SCALE-Goldeye/25.10.7/TrueNAS-SCALE-25.10.7.iso)
- [Instalace TrueNAS](https://www.truenas.com/docs/scale/gettingstarted/install/installingscale/)
- [Zdrojové kódy sestavení instalačního média](https://github.com/truenas/scale-build)
