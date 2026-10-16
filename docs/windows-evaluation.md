# Windows Evaluation ISO additions

Reviewed: 2026-10-16. All images below are English (US), x64.

Every listed direct URL passed HTTP 206, Content-Range bytes 32768-32831/size and ISO9660 signature checks.
Only 64 bytes were read. Full hashes, iPXE booting and Windows installation have not been tested.
An ISO being bootable from USB/DVD does not guarantee SAN boot or that Windows Setup can access the source.

| Image | Trial | Official source | Direct ISO |
| --- | --- | --- | --- |
| Windows 11 Enterprise | 90 days | [Microsoft Evaluation Center](https://www.microsoft.com/en-us/evalcenter/download-windows-11-enterprise) | [ISO](https://software-static.download.prss.microsoft.com/dbazure/26300.9457.260913-1737.26h2_ge_release_svc_refresh_CLIENTENTERPRISEEVAL_OEMRET_x64FRE_en-us.iso) |
| Windows 11 Enterprise LTSC 2024 | 90 days | [Microsoft Evaluation Center](https://www.microsoft.com/en-us/evalcenter/download-windows-11-enterprise) | [ISO](https://software-static.download.prss.microsoft.com/dbazure/888969d5-f34g-4e03-ac9d-1f9786c66749/26100.1742.240906-0331.ge_release_svc_refresh_CLIENT_LTSC_EVAL_x64FRE_en-us.iso) |
| Windows 11 IoT Enterprise LTSC 2024 | 90 days | [Microsoft Evaluation Center](https://www.microsoft.com/en-us/evalcenter/download-windows-11-iot-enterprise-ltsc-eval) | [ISO](https://software-static.download.prss.microsoft.com/dbazure/998969d5-f34g-4e03-ac9d-1f9786c66749/26100.1742.240906-0331.ge_release_svc_refresh_CLIENT_IOT_LTSC_EVAL_x64FRE_en-us.iso) |
| Windows Server 2016 | 180 days | [Microsoft Evaluation Center](https://www.microsoft.com/en-us/evalcenter/download-windows-server-2016) | [ISO](https://software-static.download.prss.microsoft.com/pr/download/Windows_Server_2016_Datacenter_EVAL_en-us_14393_refresh.ISO) |
| Windows Server 2019 Essentials | 180 days | [Microsoft Evaluation Center](https://www.microsoft.com/en-us/evalcenter/download-windows-server-2019-essentials) | [ISO](https://software-static.download.prss.microsoft.com/pr/download/17763.737.190906-2324.rs5_release_svc_refresh_SERVERESSENTIALS_OEM_x64FRE_en-us_1.iso) |
| Windows Server 2016 Essentials | 180 days | [Microsoft Evaluation Center](https://www.microsoft.com/en-us/evalcenter/download-windows-server-2016-essentials) | [ISO](https://download.microsoft.com/download/6/9/5/6957BB28-1FAD-4E62-B161-F873196130BD/14393.0.161119-1705.RS1_REFRESH_SERVERESSENTIALS_OEM_X64FRE_EN-US.ISO) |

Windows Server 2025, 2022 and 2019 were added previously; see `windows-server.ipxe`.
