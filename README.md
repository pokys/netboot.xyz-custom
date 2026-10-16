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
