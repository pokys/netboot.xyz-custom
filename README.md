## netboot.xyz-custom

Fork me!  This repo will allow you to create custom menus within netboot.xyz.
It works by using your github user name that you input and chains to this URL:

    https://raw.githubusercontent.com/${github_user}/netboot.xyz-custom/master/custom.ipxe

Once forked, you can edit the menu as much as you want.  You can compile the iPXE image to
set the `github_user` name early on so that your Github user name is set ahead of time and
will automatically display your custom submenu on boot.  You can also set your Github user
name from the Utilities menu (**Tools:** -> **Utilities** -> **netboot.xyz tools:**) which
will cause a custom menu to appear in the main menu.

If you are new to iPXE scripting, take a look at `custom.ipxe.example` and build up from that.

## Alpine Live - Tailcat-OneShot

V sekci **Live tools** vyber **Alpine Live - Tailcat-OneShot**. Samostatný profil nabootuje do RAM
a rovnou otevře interaktivní konzolové menu **SERVER / CLIENT / FORWARD** z [Tailcat-OneShot](https://github.com/pokys/Tailcat-OneShot).
Režim spojení vybíráš ručně. Součástí je i nástroj pro volitelný QR kód v režimu SERVER.

K dispozici je **Alpine 3.24 / Latest stable** a **DHCP / Static IPv4**, doporučené jsou **2 GB RAM**.
Skript je připnutý na ověřený commit a při stažení se kontroluje jeho SHA256. Všechny soubory jsou dočasné.
Po ukončení helperu lze otevřít menu znovu, přejít do shellu, restartovat nebo vypnout VM.
[Podrobnosti, zdroje a ověření](docs/alpine-tailcat.md).

## Alpine Live - Docker + Dockge + SSH

V sekci **Live tools** vyber **Alpine Live - Docker + Dockge + SSH**, potom pevnou větev **Alpine 3.24**
nebo **Latest stable** a síť přes **DHCP / Static IPv4**. Profil běží v RAM, připraví Docker a Compose,
spustí Dockge a SSH. Potřebuje internet a doporučeně alespoň **8 GB RAM**.
Latest stable používá aktuální stabilní větev Alpine pro kernel, initramfs, modloop i repozitáře balíčků;
Alpine 3.24 zůstává dostupné jako pevná větev.

- **Dockge:** `http://<IP>:5001`, účet vytvoříš při prvním otevření.
- **SSH:** `ssh root@<IP>`, náhodné heslo se zobrazí na konzoli při každém bootu.
- **Všechna data jsou dočasná:** kontejnery, images, volumes, Compose soubory i účty po restartu zmizí.

Žádné disky se automaticky nepřipojují ani neformátují. Kernel/initramfs/modloop jsou z oficiálního Alpine CDN,
balíčky z repozitářů Alpine, Dockge z Docker Hubu s připnutým digestem. Malý konfigurační archiv je v tomto repozitáři.
[Podrobnosti, údržba a ověření](docs/alpine-docker.md).

## Windows Evaluation installer menu

Položka **Windows 11 - Microsoft Evaluation** nabízí anglické x64 obrazy:

- Windows 11 Enterprise Evaluation
- Windows 11 Enterprise LTSC 2024 Evaluation
- Windows 11 IoT Enterprise LTSC 2024 Evaluation

Jde o **90denní Evaluation**. Submenu Windows Server je doplněné o **Server 2016** a **Server Essentials 2019 / 2016**,
vše jako **180denní Evaluation, EN x64**. Essentials nabízí jiné edice/volby než Standard/Datacenter ISO.
Všechny nové URL pocházejí z Microsoft Evaluation Center a prošly 16. 10. 2026 kontrolou HTTP Range + ISO9660.
[Seznam nových obrazů a oficiálních zdrojů](docs/windows-evaluation.md).

Menu vypisuje zdroj a URL, při chybě nabízí opakování a návrat. Používá přímý ISO `sanboot`.
Funkčnost síťového bootu ani instalace není ověřená; podle firmwaru a Windows Setup může být potřeba
WinPE/wimboot se samostatným instalačním zdrojem. Menu nespouští bezobslužnou instalaci.

## Windows Server installer menu

V custom menu vyber **Windows Server - Microsoft Evaluation**. K dispozici jsou anglické x64 ISO:

- [Windows Server 2025](https://www.microsoft.com/en-us/evalcenter/download-windows-server-2025)
- [Windows Server 2022](https://www.microsoft.com/en-us/evalcenter/download-windows-server-2022)
- [Windows Server 2019](https://www.microsoft.com/en-us/evalcenter/download-windows-server-2019)

Všechny položky používají přímé ISO URL na `software-static.download.prss.microsoft.com`.
Jde o **180denní Evaluation obrazy**, nikoli plná licenční média. Standard/Datacenter a Server Core/Desktop Experience
vybíráš v instalátoru. Menu nepředává automatickou instalaci ani nevybírá cílový disk.
Před bootem vypíše zdroj a přesnou URL; při chybě nabídne opakování nebo návrat.

Dne 16. 10. 2026 prošly všechny tři URL kontrolou HTTP 206, rozsahu bytes 32768-32831 a ISO9660.
Kontrola neověřuje celý hash ani funkčnost síťového bootu. Používá se `sanboot` stejně jako u původní Windows 11 položky.
Podpora závisí na iPXE, firmwaru a dostupnosti média ve Windows Setup; může být potřeba WinPE/wimboot
a samostatný instalační zdroj. Boot ani instalace zatím nebyly otestovány.

## XCP-ng installer menu

V sekci Virtualization vyber **XCP-ng - Official downloads**. Menu obsahuje všech **20 instalačních ISO**
z oficiálních adresářů verzí **8.3, 8.2, 8.1, 8.0, 7.6 a 7.5**, včetně Full ISO a Netinstall.
Řada **8.3 je LTS**, starší řady jsou označené jako Historical. U 8.3 zůstávají samostatné i datované revize.
Netinstall vyžaduje síťový zdroj instalačních balíčků; Full ISO je obsahuje na médiu.

Stahuje se přímo z `https://updates.xcp-ng.org/isos/`. Před bootem se zobrazí zdroj, název a přesná URL.
[Seznam obrazů](docs/xcp-ng-images.md) obsahuje výsledky malých HTTP Range/ISO9660 kontrol ze 16. 10. 2026.
Úplné hashe/podpisy ani skutečný boot a instalace nejsou ověřené. Menu používá ISO `sanboot`;
[oficiální alternativa PXE/iPXE](https://docs.xcp-ng.org/installation/install-xcp-ng/) vyžaduje rozbalené instalační médium na HTTP serveru.
Při chybě se lze vrátit do stejného seznamu nebo pokus opakovat. Instalace je interaktivní, bez answerfile.

## ESXi installer menu

V custom menu vyber **VMware ESXi - Select source**. Nejprve zvolíš server, potom výrobce a verzi:

- **Dell - official downloads**: přímé URL na serverech Dellu.
- **MahanServer - third-party mirror**: kopie z MahanServeru.
- **Hausmer - third-party mirror**: odkazy ze seznamu Hausmer.
- **Digiboy - third-party mirror**: přímé odkazy z živého serveru `vmware.digiboy.ir`.

Katalog obsahuje **221 různých názvů ISO** a **229 download URL**. Digiboy přidává 35 URL,
z toho 29 názvů nebylo v předchozím katalogu. Obsahuje i Dell ESXi 9.0 A00, novější standardní obrazy,
HPE, Cisco a samostatně označený komunitní obraz s RTL8111.
Stejný název na různých serverech neprokazuje totožný obsah. Různé buildy a revize Axx zůstávají samostatné;
u přejmenovaných Dell ISO bez revize se revize nevymýšlí. Patch/depot ZIPy nejsou bootovací ISO.

Každá stránka má nejvýše 12 obrazů. Před bootem se vypíše zdroj a přesná URL.
Menu nepřepíná mirror automaticky; při chybě lze opakovat pokus nebo se vrátit k výběru zdroje.
Původní Dell ISO z MahanServeru zůstává dostupné přímo v sekci MahanServer.
URL jsou pevné; dřívější přepis `esxi_mirror_base_url` se již nepoužívá, aby název zdroje odpovídal skutečnému serveru.

[Úplný seznam URL a kontrol](docs/esxi-images.md) se generuje z [katalogu](catalog/esxi.json).
Kontroly patří ke konkrétní URL, ne automaticky ke všem kopiím téhož názvu.

### Co je skutečně ověřené

Průzkum Dellu ze 16. 10. 2026 zahrnul **144 veřejných produktových indexů** a **63 stránek Dell Support**.
[Audit](catalog/dell-discovery.json) zaznamenává rozsah i stránky bez přímého ISO odkazu.
Oficiální část obsahuje 176 různých názvů Dell ISO; nejde o úplný seznam všech historických nebo účtem chráněných vydání.
Dell Support pro ESXi 9.0 A00 neposkytl přímé ISO; kopie z Digiboy proto patří do sekce třetí strany.

U všech **35 Digiboy URL** prošla kontrola HTTP Range + ISO9660. Celkem je potvrzeno **46 URL**;
ostatní mají značku **`[?]`**. Starší kontroly ostatních zdrojů nebyly při této úpravě opakovány.
Výsledek a dostupnost závisejí také na síti a pravidlech serveru. Kontrola čte jen 64 bytů ze sektoru ISO,
nestahuje celé obrazy, neověřuje úplný hash a nepotvrzuje úspěšný boot.
SHA256 zveřejněné Dellem jsou referenční metadata u oficiálních URL; `sanboot` je automaticky neověřuje.

Digiboy používá živý server, ne archivní kopii Wayback. Historický archiv může obsahovat další soubory;
jeho obsah zatím nebyl porovnán se živým serverem.

### Boot a aktualizace katalogu

ISO se čte přes iPXE `sanboot`. Instalaci a cílový disk vybíráš v instalátoru ESXi, bez kickstartu.
Zvláště u starších verzí a UEFI může mít ISO SAN boot omezení; alternativou je rozbalený instalátor přes HTTP.
Menu se neaktualizuje při každém bootu. Po úpravě katalogu spusť standardním Pythonem:

```text
python tools/esxi_catalog.py
python tools/esxi_catalog.py --check
python -m unittest discover -s tests -v
```

Aktualizace kontrol všech primárních i alternativních URL (pouze malé Range požadavky):

```text
python tools/esxi_catalog.py --verify-network
```

Opakovaný průzkum veřejného archivu Dellu vytvoří kandidáty v ignorovaném `.build/dell-discovery/`,
nemění zkontrolovaný katalog. Novější stránky Dell Support vyžadují samostatné dohledání.

```text
python tools/discover_dell_esxi.py
```

## Ventoy LiveCD

V **Live tools** vyber **Ventoy LiveCD - USB installer / updater**. Oficiální LiveCD
**1.1.18** otevře grafický nástroj pro instalaci/aktualizaci Ventoy na ručně vybraném USB či disku.
Používá přímo ISO z oficiálního GitHub release, bez vlastního assets serveru.
[Zdroj, SHA256 a rozsah ověření](docs/ventoy-livecd.md).

## Puppy Linux a Slax

V **Live tools** jsou **Puppy Linux - BookwormPup64 10.0.12** (4 GB RAM)
a **Slax - Debian 12.2.0** (2 GB RAM). Obě x86_64 distribuce bootují do RAM bez persistence.
Připravené bootovací soubory jsou v GitHub Releases tohoto repozitáře;
Slax si navíc načítá ISO z mirroru ČVUT. V původním netboot.xyz tyto dvě distribuce nejsou.
Obě prostředí prošla bootem až na desktop v QEMU bez disku.
[Zdroje, příprava a rozsah ověření](docs/puppy-slax.md).

## Alpine Live - App appliances

V **Live tools → Alpine Live - App appliances** lze před bootem zaškrtnout
**Nextcloud, Copyparty, Wastebin, Semaphore UI, Caddy, Uptime Kuma, Apache Guacamole**
a navíc **IT-Tools**. Společný Alpine základ vždy připraví Docker, Dockge a SSH;
jednotlivé aplikace jsou samostatné Compose stacky v Dockge. Funguje výběr Alpine větve
i DHCP / statická IPv4. Prázdný výběr spustí původní Docker lab.

Vše je dočasné v RAM, včetně databází, uploadů a účtů. Pro lehký výběr doporučeně
8 GB RAM, pro celý výběr 16 GB. Přístupové adresy a náhodné heslo se zobrazí na konzoli;
podrobnosti lze vypsat přes SSH příkazem `live-apps status`.
[Porty, správa, zdroje a ověření](docs/alpine-apps.md).
