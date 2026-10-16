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

## ESXi z MahanServer mirroru

V custom menu vyber **VMware ESXi - MahanServer mirror**. `esxi.ipxe` nabízí 12 ISO obrazů:

- ESXi 8.0 U3 Standard, Dell A00 a HPE; také 8.0 U1 Standard.
- ESXi 9.0 HPE a HPE Superdome Flex. Generické ESXi 9 ISO na mirroru při kontrole nebylo.
- ESXi 7.0 U3f Standard a HPE z července 2022.
- ESXi 6.7 U3 HPE, 6.5 U2 Standard, 6.5 U3 HPE a 6.0 U3 HPE.

ISO se čte přímo z [mirroru](https://mirror.mahanserver.net/VMware/ESXI/) pomocí iPXE `sanboot`.
Není potřeba sestavování, lokální rozbalování ISO ani vlastní server. Menu neobsahuje kickstart;
instalaci a cílový disk volíš v instalátoru ESXi. Patch/depot ZIPy nejsou instalační ISO a do menu nejsou zahrnuté.

URL a podpora HTTP Range (`206 Partial Content`) byly ověřeny 16. 10. 2026.
To ověřuje dostupnost a čtení obrazu, nikoliv úspěšný start instalátoru na konkrétním stroji nebo původ obsahu ISO.
Přímý ISO SAN boot závisí na iPXE a firmwaru, zejména v UEFI; není ekvivalentem připojeného ISO přes iLO/iDRAC.
Pokud instalátor nenaběhne nebo nenajde médium, standardní alternativa je rozbalený ESXi instalátor přes HTTP
(`mboot.efi`/`bootx64.efi` a upravený `boot.cfg`); tato varianta není součástí tohoto jednoduchého menu.

V `boot.cfg` lze přepsat kořen mirroru (bez koncového lomítka, se stejnými podadresáři a názvy ISO):

```ipxe
set esxi_mirror_base_url https://mirror.mahanserver.net/VMware/ESXI
```

Menu se samo neaktualizuje podle obsahu mirroru. Další ISO přidej jako položku a label v `esxi.ipxe`.
Na cílovém stroji je ještě potřeba ověřit skutečný síťový boot. Spuštění menu samo žádný disk nemaže.
