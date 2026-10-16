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
