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

V custom menu vyber **VMware ESXi - Select version**. Nabídka je rozdělená na **Standard / Dell / HPE**,
dále podle verzí a po nejvýše 12 obrazech na stránku. Každá položka uvádí build; u Dellu také revizi Axx.

Katalog obsahuje **192 různých ISO obrazů**:

- **176 Dell customized** přímo z `downloads.dell.com` / `dl.dell.com`, včetně historických verzí 3.5 až 8.0.
- **9 standardních obrazů** z MahanServeru a [Hausmerova seznamu](https://hausmer.com/posts/vmware-downloads/#esxi), včetně ESXi 9.0, 8.0 U3e/U3b/U2b a 7.0 U3n.
- **7 HPE obrazů** z [MahanServeru](https://mirror.mahanserver.net/VMware/ESXI/).

[Úplný seznam obrazů, download URL a výsledků kontroly](docs/esxi-images.md) se generuje z [katalogu](catalog/esxi.json).
Stejné názvy ISO jsou sloučené; různé buildy a revize Axx zůstávají samostatné. Historická média Installer/Recovery se rozlišují.
Patch/depot ZIPy, add-on balíčky a samotné release notes nejsou bootovací ISO.

### Co je skutečně ověřené

Průzkum ze 16. 10. 2026 zahrnul **144 veřejných produktových indexů Dellu** a **63 konkrétních stránek Dell Support**.
[Audit zdrojů](catalog/dell-discovery.json) zaznamenává rozsah i stránky bez přímého ISO odkazu.
Archiv obsahoval 141 různých názvů ISO; další byly dohledány v Dell Support. Nejde o tvrzení, že jsou veřejně dostupná všechna kdy vydaná nebo účtem chráněná ISO.
Například u Dell ESXi 9.0 A00 se našly pouze release notes s odkazem na Broadcom; neexistující přímá URL se nevymýšlí.

Poslední kontrola HTTP Range + ISO9660 prošla u **11 primárních URL**. **Ostatních 181 URL vracelo z ověřovacího připojení HTTP 403**, a proto mají v menu značku **`[?]`**.
Tyto odkazy pocházejí ze zveřejněných zdrojů, ale jejich aktuální dostupnost nelze potvrdit. Vyzkoušej je ze své sítě; výsledek může záviset na serveru nebo jeho přístupových pravidlech.
Pokud boot selže, lze se vrátit do stejného seznamu, zopakovat pokus nebo použít jiný doložený zdroj, pokud je v katalogu uvedený.
Původní Dell 8.0 U3 A00 z MahanServeru je zachován jako taková alternativa k primární URL Dellu.

Kontrola čte jen 64 bytů ze sektoru ISO, nestahuje celé obrazy a nepotvrzuje úspěšný boot.
U **41 obrazů** je uložený také SHA256 zveřejněný Dellem. Je to údaj pro kontrolu celého staženého souboru;
`sanboot` ho automaticky neověřuje.

### Boot a aktualizace katalogu

ISO se čte přímo přes iPXE `sanboot`; není potřeba vlastní sestavování ani server s rozbalenými obrazy.
Instalaci a cílový disk vybíráš v instalátoru ESXi, bez kickstartu. Zvláště u starých verzí a UEFI může mít ISO SAN boot omezení;
alternativou je rozbalený instalátor přes HTTP (`mboot.efi`/`bootx64.efi` a `boot.cfg`).

Pro MahanServer odkazy lze přepsat kořen mirroru v `boot.cfg` (bez koncového lomítka):

```ipxe
set esxi_mirror_base_url https://mirror.mahanserver.net/VMware/ESXI
```

Dell a Hausmer používají vlastní absolutní URL. Menu se automaticky neaktualizuje při každém bootu.
Po úpravě `catalog/esxi.json` spusť standardním Pythonem, bez dalších balíčků:

```text
python tools/esxi_catalog.py
python tools/esxi_catalog.py --check
python -m unittest discover -s tests -v
```

Nová síťová kontrola (malé Range požadavky, mění záznamy kontroly a přegeneruje menu):

```text
python tools/esxi_catalog.py --verify-network
```

Opakovaný průzkum veřejného archivu Dellu vytvoří kandidáty v ignorovaném `.build/dell-discovery/`:

```text
python tools/discover_dell_esxi.py
```

Tento průzkum nemění zkontrolovaný katalog. Novější Dell Support stránky vyžadují samostatné dohledání;
část obsahuje pouze release notes a přesměrování na Broadcom.
