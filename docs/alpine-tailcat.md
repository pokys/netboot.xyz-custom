# Alpine Live: interactive Tailcat-OneShot

Choose **Live tools → Alpine Live - Tailcat-OneShot**. Select Alpine **3.24** or **Latest stable**,
then **DHCP** or **Static IPv4**. This boots a separate, diskless x86_64 Alpine environment.
Internet access is required; 2 GB RAM is recommended.

After networking starts, the local console (`tty1`) and serial console (`ttyS0`) open the interactive
[Tailcat-OneShot](https://github.com/pokys/Tailcat-OneShot) menu automatically:

- **SERVER**: start a temporary exit-node session and display its connection token.
- **CLIENT**: connect to a token and run a local SOCKS5 proxy.
- **FORWARD**: forward a local TCP port through a Tailcat session.
- **Q**: quit the helper and return to the live-console controls.

You select the mode yourself. Booting does not automatically expose the host or LAN.
The upstream script downloads Tailcat v0.6.0 only after a session mode is selected and verifies
its release checksum. `libqrencode-tools` is included so SERVER mode can offer its optional QR code.
Linux CLIENT mode prints proxy settings; it does not launch a browser in this console-only profile.

After quitting or an error, press Enter to reopen Tailcat, `s` for a local shell, `r` to reboot,
or `p` to power off. Exiting the shell returns to those controls. This profile starts neither Docker,
Dockge nor SSH; its interactive terminal runs locally with administrative access.

All files and session state live in RAM. Host disks are not automatically mounted or formatted.
After reboot, the environment starts clean. Normal helper shutdown cleans up its Tailcat process
and runtime directory. Treat any active connection token as a temporary access credential.

## Script source and updates

The console downloads this reviewed script over HTTPS:

- Repository: [pokys/Tailcat-OneShot](https://github.com/pokys/Tailcat-OneShot).
- Commit: `b6f66419a2971e01f3db4f2959551950006b9bac`.
- File: `Tailcat_OneShot.sh`.
- SHA256: `7f65d6de7d43466b6d7f7eba781568599c81943f60ab1af7120f661e8ea72d4d`.

The download is verified before execution and atomically moved into place. A failed download/hash check
leaves the console available for retry or network diagnosis. The helper is not automatically updated to
an unreviewed upstream commit; update the URL and hash together in `tailcat-console` when upgrading.

Sources are in `alpine/tailcat-overlay/`. The network configuration scripts are shared from the Docker
profile by the archive builder, so DHCP/static IPv4 behavior stays the same. Each profile has its own
configuration archive and package list. Alpine's selected branch supplies both boot files and APK repositories.

```text
python tools/build_alpine_overlay.py --profile tailcat
python tools/build_alpine_overlay.py --profile tailcat --check
python tools/build_alpine_overlay.py --check
python -m unittest discover -s tests
```

Commit both source changes and `alpine/tailcat-live.apkovl.tar.gz`. The archive contains configuration only,
with deterministic root ownership/timestamps; it embeds no credentials or session tokens.

## Validation

On 2026-10-16 this profile booted in a diskless x86_64 QEMU VM with 2 GB RAM. The verified wrapper
opened its menu automatically on the serial console. SERVER/CLIENT/FORWARD choices were displayed;
Quit, shell access, returning from the shell and reopening the menu were exercised. The root filesystem
was tmpfs and `qrencode` was available. The upstream Tailcat binary downloaded, passed its release checksum
and ran `--help` on Alpine. No exit-node/proxy session was opened during validation, so end-to-end remote
connectivity and QR scanning remain untested. The graphical console and physical netboot need a hardware check.
