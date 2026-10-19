# netboot.xyz custom menu

Vlastní menu pro účet `pokys`. Windows 10 / 11 se instalují přes **iPXE → wimboot → WinPE → OSDCloud**.
OSDCloud stáhne instalační obraz z Microsoftu až při nasazení. V menu je také samostatné ESXi submenu.

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

## Sestavení WinPE

Bez instalace nástrojů na vlastní PC spusť v GitHubu **Actions → Build Windows installer
boot files → Run workflow**. Workflow na dočasném Windows runneru nainstaluje ADK/WinPE,
sestaví obraz a zveřejní `boot.wim`, `osdcloud.iso`, `wimboot`, `BCD`, `boot.sdi` a `SHA256SUMS`
pod tagem nastaveným v `OSDCLOUD_RELEASE_TAG` ve workflow. ISO obsahuje totožný `sources/boot.wim` jako netboot;
jeho hash je také v `SOURCE-WIM-SHA256.txt`. Obraz obsahuje podepsané x64 ovladače VirtIO SCSI,
VirtIO Block, NetKVM, VMware PVSCSI a VMXNET3. CAB balíčky z Microsoft Update
Catalog mají připnuté SHA256 a build ověřuje podpisy Microsoft WHCP.
Seznam verzí a zdrojů je v `scripts/winpe-virtual-drivers.json` a v release.
Záznamy s `pe: false` jsou kompatibilní varianty jen pro cílový systém;
do PE se neinjektují. Build odmítne více variant stejného INF v PE.
Build přibalí stejné podepsané balíčky i pro cílové Windows. Závěrečný hook OSDCloud
je přidá do offline instalace při detekci VirtIO nebo VMware PCI zařízení;
u VMware vybere variantu INF podle buildu cílového jádra, protože balíčky pro novější
Windows nejsou použitelné pro všechny starší verze. Tím se řeší i ovladač systémového
disku po prvním restartu, nejen jeho viditelnost v PE.
Boot testy zavádějí WinPE přes iPXE i přímo z ISO v BIOS/UEFI a s virtuálními řadiči,
ověřují detekci disku, HTTP síť a PowerShellGet/NuGet pomocí `Find-Module`;
instalaci Windows nespouští. Samostatný workflow **Validate complete OSDCloud deployments**
provádí skutečné nasazení Windows 10 a 11 přes GUI do nových testovacích disků na GitHub runneru
a kontroluje stažení, aplikaci obrazu, ovladače, BCD a následný start do OOBE.
Test odmítá běžet mimo označenou dočasnou CI VM. Výsledky obou druhů testů ověř před použitím nového release;
samotné zveřejnění souborů nepotvrzuje úspěšnou instalaci.
Existující release nepřepisuje. Následující postup je alternativa pro lokální sestavení.

Nainstaluj [Windows ADK](https://learn.microsoft.com/en-us/windows-hardware/get-started/adk-install)
(komponentu **Deployment Tools**) a odpovídající **Windows PE add-on** doporučené Microsoftem pro cílové Windows 11.
Potřebuješ internet, několik GB volného místa a 64bitový **Windows PowerShell 5.1 jako správce**.
Z kořene repozitáře spusť:

```powershell
# Je-li potřeba, nejprve zpřístupni NuGet provider pro Save-Module:
Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Scope CurrentUser -Force
.\scripts\Build-OSDCloud.ps1
```

Build přidá do WinPE PowerShell, standalone modul **OSD 26.10.6.1** a interaktivní launcher.
Součástí jsou PowerShellGet **2.2.5**, PackageManagement **1.4.8.1** a offline
NuGet provider, které OSDCloud potřebuje po stisku Start. Obraz připraví
profilové cesty vyžadované PowerShellGet a obsahuje Microsoft.PowerShell.Archive
**1.2.5** pro rozbalování ZIP balíčků ovladačů. Pro stejné virtuální
ovladače při lokálním sestavení nejprve spusť `scripts/Get-WinPEVirtualDrivers.ps1 -DestinationPath .build/virtual-drivers` a sestavení předej `-DriverPath .build/virtual-drivers`.
OSD obsahuje implementaci OSDCloud; nové sestavovací nástroje OSDeploy zde nejsou potřeba.
Součástí jsou také připnuté x64 nástroje curl **8.23.0_1** s CA certifikáty,
7-Zip **26.04** a podepsaný Microsoft `setx.exe`. Verze, zdroje a kontrolní součty
uvádí `runtime-manifest.json`. Launcher před nabídkou instalace ověří příkazy,
moduly, rozbalování archivů, čtení WIM pomocí DISM a skutečné stahování přes OSD i curl.
Při chybě zapíše diagnostiku do `%TEMP%\OSDCloud-Requirements.json` a instalaci nezahájí.
Build také opravuje kolizi přepínače `$WebClient` s objektem stejného jména ve
funkci `Save-WebFile` z OSD 26.10.6.1. Oprava ověřuje SHA256 původního i výsledného
zdroje. Regresní test reprodukuje chybu a ověřuje skutečné HTTP stažení bez curl
i s explicitním `-WebClient`, bez spuštění instalace Windows.
Výstup je `artifacts/osdcloud/boot.wim`, `wimboot`, `BCD`, `boot.sdi` a `SHA256SUMS`.
Pro lokální vytvoření odpovídajícího ISO potom spusť `scripts/Build-OSDCloudIso.ps1`;
výstup je `artifacts/osdcloud-iso/osdcloud.iso`. GitHub workflow oba výstupy spojí do stejného release.
BCD a `boot.sdi` pocházejí ze stejného WinPE add-onu a iPXE je předává explicitně;
samotný základní ADK WIM neobsahuje kompletní bootovací médium.
**wimboot v2.9.0** se kontroluje proti pevně zadanému SHA256. Aktualizace verzí vyžaduje nové ověření a build.
Binární obrazy a pracovní soubory Git ignoruje. Žádné Windows ISO se při buildu nestahuje.
Build nespouští instalaci Windows ani neformátuje disk.

Při ověřování v Proxmoxu pomohla u testované VM změna CPU na `host`;
s původním `x86-64-v2-AES` se PE zastavilo na logu. Jde o výsledek konkrétního testu,
nikoli o požadavek měnit všechny VM. CI používá KVM s CPU `host`.

Ve VMware Workstation používej profil **Windows 11 x64**, firmware **UEFI**
a podporovaný řadič systémového disku. U testované VM s diskem na SATA zůstával
zapnutý prázdný LSI SCSI řadič a profil Other Linux / BIOS; po změně profilu,
UEFI a vypnutí tohoto řadiče PE prošlo inicializací a začalo kontrolovat závislosti.
Samostatně tím není prokázaná příčina původního `DRIVER_PNP_WATCHDOG`.
CI testy VMware řadičů používají PVSCSI a VMXNET3 emulované v QEMU;
ověření ve VMware Workstation je další ruční test.

Síťové a storage ovladače musí být dostupné už ve WinPE. Chybějící rozbalené podepsané x64 INF ovladače přidej takto:

```powershell
.\scripts\Build-OSDCloud.ps1 -DriverPath C:\Drivers\WinPE
```

Skript odmítne přepsat existující `boot.wim` nebo použít existující pracovní adresář.
Pro opakovaný build zvol nové adresáře:

```powershell
.\scripts\Build-OSDCloud.ps1 -WorkPath C:\OSDCloudBuild\build2 -OutputPath C:\OSDCloudBuild\output2
```

## Vystavení bootovacích souborů

Výchozí menu očekává tyto adresy:

```text
https://github.com/pokys/netboot.xyz-custom/releases/download/osdcloud-v8/boot.wim
https://github.com/pokys/netboot.xyz-custom/releases/download/osdcloud-v8/wimboot
https://github.com/pokys/netboot.xyz-custom/releases/download/osdcloud-v8/BCD
https://github.com/pokys/netboot.xyz-custom/releases/download/osdcloud-v8/boot.sdi
```

Po ručním buildu vytvoř GitHub Release s novým tagem a přilož všechny čtyři soubory
a `SHA256SUMS`; při jiném tagu uprav URL v menu.
Při ručním sestavení se release a binární soubory automaticky nepublikují.

Alternativou je assets server netboot.xyz nebo jiný HTTP(S) server v LAN. V `boot.cfg` nastav:

```ipxe
set osdcloud_base_url http://192.168.1.10:8080/osdcloud
```

Adresář musí obsahovat `boot.wim`, `wimboot`, `BCD` a `boot.sdi`.
URL bez koncového lomítka lze změnit i v submenu Windows.
GitHub HTTPS potřebuje funkční DNS a podporu HTTPS a důvěryhodných certifikátů v iPXE.
Při problému se stažením přes GitHub otestuj LAN HTTP server.

## Zapojení do netboot.xyz

Po publikování změn na větev `master` nastav v netboot.xyz přes **Utilities → netboot.xyz tools** GitHub uživatele `pokys`.
Případně jej nastav předem v konfiguraci:

```ipxe
set github_user pokys
```

netboot.xyz načte `https://raw.githubusercontent.com/pokys/netboot.xyz-custom/master/custom.ipxe`.
Vyber **Windows 10 / 11 - OSDCloud installer**, potom **Boot Windows PE / OSDCloud**.
Tato položka zavádí x64 WinPE přes **BIOS i x64 UEFI**. V BIOS režimu ověřuje
64bitový procesor pomocí `cpuid`, protože samotné iPXE bývá sestavené jako `i386`.
**Samotná instalace OSDCloud vyžaduje UEFI.** OSDCloud připravuje cílový disk jako GPT;
BIOS boot PE slouží k diagnostice a nepotvrzuje podporu BIOS instalace Windows.
Viz [požadavek OSDCloud na VM generace 2 / UEFI](https://www.osdcloud.com/osdcloud-v1/osdcloud/setup/osdcloud-vm/new-osdcloudvm).
Pro instalaci Windows 11 použij UEFI; BIOS cesta je určená zejména pro Windows 10.

WinPE inicializuje síť, zobrazí disky a vyžádá potvrzení `INSTALL`.
V OSDCloud pak vyber **Windows 10 22H2 x64** nebo požadovanou verzi **Windows 11**,
edici a jazyk (`cs-cz` pro češtinu). Windows 10 i 11 používají stejné WinPE a wimboot;
instalační obraz se stahuje z Microsoftu až po výběru v průvodci.
Nabídka dostupných Windows 11 vydání závisí na katalogu připnuté verze modulu OSD.
Windows 7 a 8.1 nejsou do tohoto OSDCloud menu přidané.
Ověř cílový disk v instalačních výzvách OSDCloud: jeho potvrzením povoluješ vymazání dat.
Projekt nepředává `ZTI` a sám disk nevybírá ani nemaže. Nejde o klasického průvodce `setup.exe`, ale o nasazení obrazu Windows.

## Kontrola a první boot

```powershell
.\scripts\Test-Configuration.ps1
```

Kontrola ověřuje syntaxi PowerShellu, cíle iPXE menu a ochrany launcheru pomocí mocků.
Neprovádí sestavení WIM, síťový boot ani instalaci Windows.
První úplný test proveď ve VM s x64 UEFI, funkční sítí a prázdným virtuálním diskem.
Secure Boot vyžaduje kompatibilní a důvěryhodný celý bootovací řetězec; samotný wimboot jeho funkčnost nezaručuje.
Při problému se sítí zkontroluj `ipconfig`, při chybějícím disku doplň ovladače a znovu sestav obraz.

## Zdroje

- [iPXE: wimboot a WinPE přes HTTP](https://ipxe.org/wimboot)
- [Microsoft: závislosti WinPE optional components](https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/winpe-add-packages--optional-components-reference)
- [OSD: OSDCloud a interaktivní GUI](https://github.com/OSDeploy/OSD)
- [OSDCloud: výběr operačního systému, edice a jazyka](https://www.osdcloud.com/osdcloud-v1/osdcloud/deployment/winpe/start-osdcloudgui)
- [Microsoft: instalační média Windows 10](https://www.microsoft.com/en-us/software-download/windows10)

## TrueNAS Community Edition

V **Storage / NAS → TrueNAS Community Edition - Installer** je síťový instalátor
**25.10.7**, zaváděný přímo přes iPXE kernel/initramfs. Linux přes DHCP stáhne
oficiální ISO do RAM; doporučeno 12 GB RAM (minimum 8 GB).
Cílový systémový disk vybíráš až v interaktivním instalátoru.
[Příprava souborů a rozsah ověření](docs/truenas.md).

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
