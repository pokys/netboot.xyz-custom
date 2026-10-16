# Alpine Live: Docker + Dockge + SSH

Choose **Live tools → Alpine Live - Docker + Dockge + SSH**, then **Start Alpine Docker Live**.
The profile boots Alpine v3.24 x86_64 directly from its official netboot kernel/initramfs and loads
this repository's small configuration archive. DHCP and internet access are required.
Docker packages are downloaded from Alpine main/community; Dockge is pulled from Docker Hub.
Allow a few minutes for the first startup, depending on the network and CPU.

Use **8 GB RAM or more** for useful container workloads. The root filesystem may use up to 85% of RAM;
that space is shared with package files, Docker images, layers, logs, and volumes.
Docker uses the overlay2 storage driver on the RAM filesystem to avoid copying complete image layers.
Large image collections/builds still need more RAM.

## Access

The console prints the assigned IPv4 addresses and a new random SSH password on each boot.

- SSH: `ssh root@<IP>` on port 22, using the password printed on the console.
- Dockge: `http://<IP>:5001`; create a Dockge account on first visit.
- Compose files: `/opt/stacks`; Dockge's own stack: `/opt/dockge/compose.yaml`.
- Display connection information again: `cat /run/docker-live/access.txt`.

The SSH password and host keys are generated in the live environment, never stored in Git.
SSH runs with administrative access so you can manage Docker. Dockge also controls the Docker daemon.
The profile starts no other application stacks automatically.

Everything is temporary: **Docker images, containers, volumes, Compose files, Dockge accounts,
SSH keys and passwords disappear after power-off/reboot**. No host disks are automatically mounted,
partitioned or formatted by this profile. A container or administrator can explicitly access disks.

If Dockge's image download fails, SSH remains available. Retry with `rc-service dockge-live restart`.
Inspect services using `rc-status`; Docker's log is available at `/var/log/docker.log`.
In a RAM-backed live session, avoid large images/builds that exhaust memory.

## Updating the configuration

Edit files under `alpine/overlay/` and rebuild the archive with standard Python:

```text
python tools/build_alpine_overlay.py
python tools/build_alpine_overlay.py --check
python -m unittest discover -s tests
```

Commit both source changes and `alpine/docker-live.apkovl.tar.gz`. The archive contains configuration
and startup scripts only, with deterministic root ownership and timestamps; no personal filesystem metadata.
The Docker/Compose versions follow Alpine's stable v3.24 repositories. Dockge's upstream `:1` image
is pinned by manifest digest in `compose.yaml`; update the digest deliberately when upgrading.

The main menu and `alpine-docker.ipxe` point at files on the `master` branch of this repository.
Alpine's branch netboot files can receive updates, so the kernel/initramfs/modloop must stay from the same branch.

## Validation

On 2026-10-16 the profile booted successfully in a diskless x86_64 QEMU VM with 4 GB RAM.
The VM fetched the same configuration archive and official Alpine packages, using local HTTP for the
test copy of the archive/modloop. Root was confirmed as tmpfs, Docker used overlay2, an Alpine test
container ran successfully, SSH password authentication worked, and Dockge reported healthy with
HTTP 200 from its web interface. Docker Compose configuration and all three services were checked.
The final iPXE chain and physical BIOS/UEFI hardware still need a real netboot test.

## Sources

- [Alpine diskless mode](https://wiki.alpinelinux.org/wiki/Diskless_Mode)
- [Alpine netboot files](https://dl-cdn.alpinelinux.org/alpine/v3.24/releases/x86_64/netboot/)
- [Alpine initramfs boot implementation](https://gitlab.alpinelinux.org/alpine/mkinitfs/-/blob/master/initramfs-init.in)
- [Dockge's upstream Compose configuration](https://github.com/louislam/dockge/blob/master/compose.yaml)
