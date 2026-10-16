# Puppy Linux a Slax

Kontrola veřejného `https://boot.netboot.xyz/live.ipxe`, stromu šablon a `endpoints.yml`
na větvi `master` upstream netboot.xyz dne 16. října 2026 nenašla Puppy ani Slax.
Fatdog64 v původním menu je jiná distribuce.

V custom menu jsou obě položky v **Live tools**, pouze pro **x86_64**:

| Položka | Verze | Doporučená RAM | Zdroj |
| --- | --- | --- | --- |
| Puppy Linux - BookwormPup64 | 10.0.12 | 4 GB | Puppy mirror NLUUG, připravené soubory v GitHub Release tohoto repozitáře |
| Slax - Debian | 12.2.0 | 2 GB | Kernel/initramfs v GitHub Release tohoto repozitáře, ISO ze Slax mirroru ČVUT |

Obě prostředí běží v RAM bez persistence. Boot nevybírá instalační disk;
případné připojování disků, ukládání nebo instalaci spouštíš až ručně v live systému.

## Puppy

[Oficiální web Puppy](https://puppylinux-woof-ce.github.io/) uvádí NLUUG mezi mirrory.
Použitý obraz je [BookwormPup64 10.0.12](https://ftp.nluug.nl/os/Linux/distr/puppylinux/puppy-bookwormpup/BookwormPup64/10.0.12/).
Celé ISO bylo ověřeno proti publikovanému SHA256:

```text
ae65f6e6d70a96f48bdbb291c2426f8a2fd77a73692e149e81a5eecb6fe7509f
```

Kernel je původní `vmlinuz`. K původnímu `initrd.gz` je připojen standardní Linux
CPIO archiv se všemi SFS soubory z ISO a s upraveným `/init` (humongous initramfs).
Toto vydání při bootu přesune vložený hlavní SFS do `/mnt/tmpfs`, ale následně
kontroluje jeho původní cestu. Jediná změna `/init` dovoluje i soubor v `/mnt/tmpfs`;
následující upstream kód už tuto cestu umí použít.
Úpravu přesně zachycuje `tools/prepare_small_live.py`; změněný zdroj `/init` je také
samostatným souborem `puppy-init-source.sh` v release. Hlavičky původního zdroje zůstávají zachované.

Parametry `pfix=ram pmedia=cd` spouštějí čerstvé live prostředí bez načítání savefile.
Boot stahuje přibližně 794 MB. SFS, firmware a ovladače jsou součástí initramfs;
po načtení není potřeba síťový server se zbytkem systému.

Zdroje upstream: [Woof-CE](https://github.com/puppylinux-woof-CE/woof-CE),
[BookwormPup64 build files](https://ftp.nluug.nl/os/Linux/distr/puppylinux/puppy-bookwormpup/BookwormPup64/build_files/),
[zdroj kernelu 6.1.148](https://ftp.nluug.nl/os/Linux/distr/puppylinux/puppy-bookwormpup/BookwormPup64/10.0.12/kernel_sources-6.1.148-kernel-kit.sfs),
[Debian sources](https://deb.debian.org/debian/pool/).

## Slax

Kernel a `initrfs.img` jsou beze změn vytažené z téhož ISO, které se později stahuje:
[Slax Debian 12.2.0 x64](https://ftp.sh.cvut.cz/slax/Slax-Debian-12.x/).
Publikovaný MD5 `96369071b0eeed78f6bb64b8148cbb34` souhlasil s celým ISO;
MD5 slouží pouze ke kontrole shody, ne k ověření pravosti.

Používá se dokumentovaný parametr `from=http://...iso` a `toram`.
HTTP pro ISO je záměrné kvůli klientovi v initramfs Slax; přenos není šifrovaný
a Slax při bootu nekontroluje celý hash. Kernel/initramfs se stahují přes HTTPS z GitHubu.
[Oficiální dokumentace](https://www.slax.org/using.php),
[oficiální iPXE příklad](https://slax.org/ipxe/?arch=64bit),
[Linux Live Kit source](https://github.com/Tomas-M/linux-live),
[Debian package sources](https://deb.debian.org/debian/pool/).
Oficiální iPXE příklad stále ukazuje starší Slax 11.3 v již přesunutém adresáři;
custom menu používá připravené soubory z 12.2.0.

## Příprava a ověření

Reprodukovatelná příprava s Pythonem a 7-Zip (nový výstupní adresář):

```text
python tools/prepare_small_live.py puppy --output .build/puppy-assets
python tools/prepare_small_live.py slax --output .build/slax-assets
```

Lze předat už stažené ISO pomocí `--iso` a cestu k 7-Zip pomocí `--seven-zip`.
Skript nejprve ověří ISO a pak připraví soubory, manifest původu a `SHA256SUMS`.
Žádné lokální cesty ani účet uživatele se do manifestu neukládají.
Publikování release je samostatné; skript ho neprovádí.

Dne 16. října 2026 prošly oba profily testem QEMU bez disku: Puppy se 4 GB RAM
načetlo všech pět systémových SFS vrstev a otevřelo desktop/Quick Setup;
Slax se 2 GB RAM získal DHCP, načetl vzdálené ISO z ČVUT, zkopíroval systém do RAM
a otevřel desktop. Test použil stejné připravené kernel/initramfs a parametry jako menu,
s dodatečnou sériovou konzolí. Úplný řetězec firmware → iPXE → GitHub nebyl otestován;
Secure Boot ani fyzický hardware nejsou ověřené. iPXE při bootu automaticky nekontroluje SHA256.
