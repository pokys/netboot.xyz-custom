# Ventoy LiveCD

V **Live tools → Ventoy LiveCD - USB installer / updater** je oficiální
**Ventoy 1.1.18 LiveCD**, x86_64, vydané 9. října 2026.
Live prostředí otevře grafický nástroj pro instalaci nebo aktualizaci Ventoy na USB/disk.
Cílový disk vybíráš ručně v GUI; instalace může vymazat jeho obsah.
LiveCD není síťový server iVentoy ani nabídka ISO uložených na Ventoy USB.

## Zdroj a boot

- [Oficiální vydání a SHA256](https://github.com/ventoy/Ventoy/releases/tag/v1.1.18)
- [Přímé ISO](https://github.com/ventoy/Ventoy/releases/download/v1.1.18/ventoy-1.1.18-livecd.iso)
- [Dokumentace LiveCD](https://www.ventoy.net/en/doc_livecd.html)
- [iPXE sanboot](https://ipxe.org/cmd/sanboot)

ISO má 195 989 504 bytů. Menu používá `sanboot --no-describe --drive 0x80`
a HTTPS z oficiálního GitHub release; vlastní assets server není potřeba.
Při chybě se vrací do submenu. Doporučené jsou alespoň 2 GB RAM.

ISO obsahuje kernel `EFI/boot/vmlinuz` a samostatný initramfs `EFI/boot/initrd`
se systémovými moduly a Ventoy. Jeho GRUB spouští kernel s
`quiet first_run rdinit=/VTOY/init`. Live systém je součástí initramfs,
takže nepotřebuje dodatečný squashfs na síťovém serveru.

## Ověření

Dne 16. října 2026 bylo staženo celé ISO a jeho SHA256 se shodovalo s oficiálním:

```text
ee3917bd5a9973c0b2f8f3ef85048bf68ae089ec88f5561ad78b6ad308b51ab5
```

Přímé URL prošlo kontrolou HTTP 206, rozsahu bytes 32768–32831 a signatury ISO9660.
Byla ověřena struktura ISO a bootovací konfigurace. iPXE hash při bootu automaticky
nekontroluje. Úplný síťový boot a práce s USB zatím nejsou ověřené;
funkčnost SAN bootu závisí na iPXE a firmwaru. Secure Boot není ověřený.
